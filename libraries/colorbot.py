import cv2
import numpy as np
import threading
import queue
import time

# 預設 HSV 范围
UPPER_COLOR = np.array([155, 200, 255])  # HSV 上限颜色
LOWER_COLOR = np.array([140, 90, 180])   # HSV 下限颜色

class ColorBot:
    """颜色检测机器人，在后台持续检测目标像素"""
    def __init__(self, upper_color=UPPER_COLOR, lower_color=LOWER_COLOR):
        """
        参数:
            fov_size (int): 视场大小
            upper_color (np.array): HSV 上限颜色
            lower_color (np.array): HSV 下限颜色
        """
        self.upper_color = upper_color
        self.lower_color = lower_color
        
        self.result_queue = queue.Queue()  # 用于传递检测结果的队列
        self.image_queue = queue.Queue()   # 用于接收图像的队列
        self.running = False  # 控制检测线程的标志
        self.detect_thread = None  # 检测线程

    def start_detection(self):
        """启动后台检测线程"""
        if not self.running:
            self.running = True
            self.detect_thread = threading.Thread(target=self._detect_loop, daemon=True)
            self.detect_thread.start()
            print("后台颜色检测已启动")

    def stop_detection(self):
        """停止后台检测线程"""
        if self.running:
            self.running = False
            self.detect_thread.join()
            print("后台颜色检测已停止")

    def process_image(self, img):
        """将图像放入队列以供检测"""
        self.image_queue.put(img)

    def _detect_loop(self):
        """后台检测循环"""
        while self.running:
            try:
                screenshot = self.image_queue.get(timeout=0.1) 
                if screenshot is None:
                    self.result_queue.put(False)
                    continue

                hsv = cv2.cvtColor(screenshot, cv2.COLOR_BGR2HSV)
                mask = cv2.inRange(hsv, self.lower_color, self.upper_color)

                has_target = np.any(mask) 

                while not self.result_queue.empty():
                    self.result_queue.get()  
                self.result_queue.put(has_target)  
            except queue.Empty:
                while not self.result_queue.empty():
                    self.result_queue.get()  
                self.result_queue.put(False) 
            time.sleep(0.003)  

    def get_result(self) -> bool:
        """
        获取最新的检测结果

        """
        try:
            result = False
            while not self.result_queue.empty():
                result = self.result_queue.get_nowait() 
            return result
        except queue.Empty:
            return False 

if __name__ == "__main__":
    bot = ColorBot()
    bot.start_detection()
    try:
        counter = 0
        while True:
            # 模拟传入图像（交替有无目标颜色）
            dummy_img = np.zeros((192, 192, 3), dtype=np.uint8)
            if counter % 2 == 0: 
                dummy_img[50:100, 50:100] = [145, 150, 200] 
            bot.process_image(dummy_img)
            has_target = bot.get_result()
            print(f"范围内是否有目标像素: {has_target}")
            counter += 1
            time.sleep(0.1)
    except KeyboardInterrupt:
        bot.stop_detection()