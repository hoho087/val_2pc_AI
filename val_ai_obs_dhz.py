import numpy as np
import cv2
import onnx
import onnxruntime as ort
import os
from libraries import dhzbox
from libraries.colorbot import ColorBot
import math
import time
import random
from collections import deque
import threading
import socket

class MJPEG_Reader(object):
    def __init__(self, ip: str, port: int, grab_size=256):
        self.__ip = ip
        self.__port = port
        self.__sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__sock.bind((self.__ip, self.__port))
        self.__running = False
        self.__frame = None
        self.__thread = None
        self.__lock = threading.Lock()
        self.grab_size = grab_size

    def __receive_frame(self):
        buffer = bytearray()
        while self.__running:
            data, addr = self.__sock.recvfrom(65535)
            buffer.extend(data)
            start_marker = buffer.find(b'\xff\xd8')
            if start_marker == -1:
                continue
            end_marker = buffer.find(b'\xff\xd9')
            if end_marker == -1:
                continue
            if end_marker < start_marker:
                buffer = buffer[end_marker + 2:]
                continue
            jpeg_frame = buffer[start_marker:end_marker + 2]
            try:
                with self.__lock:
                    frame = cv2.imdecode(np.frombuffer(jpeg_frame, dtype=np.uint8), cv2.IMREAD_COLOR)
                    if frame is not None:
                        # 居中裁剪或縮放至 grab_size x grab_size
                        height, width = frame.shape[:2]
                        center_x, center_y = width // 2, height // 2
                        half_size = self.grab_size // 2
                        left = max(0, center_x - half_size)
                        top = max(0, center_y - half_size)
                        right = min(width, center_x + half_size)
                        bottom = min(height, center_y + half_size)
                        frame = frame[top:bottom, left:right]
                        if frame.shape[:2] != (self.grab_size, self.grab_size):
                            frame = cv2.resize(frame, (self.grab_size, self.grab_size))
                        self.__frame = frame
            except cv2.error as e:
                print(e)
            buffer = buffer[end_marker + 2:]

    def start(self):
        if not self.__running:
            self.__running = True
            self.__thread = threading.Thread(target=self.__receive_frame, daemon=True)
            self.__thread.start()

    def stop(self):
        if self.__running:
            self.__running = False
            if self.__thread is not None:
                self.__thread.join()
        self.__sock.close()

    def capture(self):
        with self.__lock:
            return self.__frame.copy() if self.__frame is not None else None

class Inference:
    def __init__(self, model_path="./libraries/瓦紫色.onnx"):
        self.model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), model_path)
        self.session = ort.InferenceSession(
            onnx.load(self.model_path).SerializePartialToString(),
            providers=['DmlExecutionProvider', 'CPUExecutionProvider']
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        print("DML初始化，模型加载成功")

    def preprocess(self, img):
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        img = cv2.resize(img, (256, 256))
        img = img.transpose(2, 0, 1).astype(np.float32) / 255.0
        return np.expand_dims(img, axis=0)

    def nms(self, inference, conf_thres=0.36, target_class=0):
        pred = np.squeeze(inference).astype(np.float32)
        if len(pred.shape) != 2 or pred.shape[1] != 7:
            return None

        boxes = pred[:, :4]
        scores = pred[:, 4]
        max_class_ids = np.argmax(pred[:, 5:], axis=1)

        valid = (max_class_ids == target_class) & (scores > conf_thres)
        boxes = boxes[valid]
        scores = scores[valid]
        
        if len(boxes) == 0:
            return None

        x1 = boxes[:, 0] - boxes[:, 2] / 2
        y1 = boxes[:, 1] - boxes[:, 3] / 2
        x2 = boxes[:, 0] + boxes[:, 2] / 2
        y2 = boxes[:, 1] + boxes[:, 3] / 2

        order = scores.argsort()[::-1]
        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])
            inter = np.maximum(0.0, xx2 - xx1 + 1) * np.maximum(0.0, yy2 - yy1 + 1)
            iou = inter / ((x2[i] - x1[i] + 1) * (y2[i] - y1[i] + 1) + 
                         (x2[order[1:]] - x1[order[1:]] + 1) * (y2[order[1:]] - y1[order[1:]] + 1) - inter)
            inds = np.where(iou <= 0.36)[0]
            order = order[inds + 1]
        
        result = np.zeros((len(keep), 5), dtype=np.float32)
        result[:, :4] = np.stack([x1[keep], y1[keep], x2[keep], y2[keep]], axis=1)
        result[:, 4] = scores[keep]
        return result

    def infer(self, img, target_class=0):
        img = self.preprocess(img)
        output = self.session.run([self.output_name], {self.input_name: img})[0]
        return self.nms(output, target_class=target_class)

def crop_for_colorbot(img, target_size=192):
    height, width = img.shape[:2]
    center_x, center_y = width // 2, height // 2
    half_size = target_size // 2
    left = max(0, center_x - half_size)
    top = max(0, center_y - half_size)
    right = min(width, center_x + half_size)
    bottom = min(height, center_y + half_size)
    return img[top:bottom, left:right]

def move_mouse(x, y):
    rounded_x = math.ceil(x) if x >= 0 else math.floor(x)
    rounded_y = math.ceil(y) if y >= 0 else math.floor(y)
    mouse.move(rounded_x, rounded_y)


def main():
    color_bot = ColorBot(upper_color=np.array([155, 200, 255]), lower_color=np.array([140, 90, 180])) # Purple
    color_bot.start_detection()

    VAL_FACTOR = 1.07437623 * pow(SENS, -0.9936827126)  # 靈敏度換算因子
    # 初始化 PID 變量
    P = [0, 0]
    I = [0, 0]
    D = [0, 0]
    past_error = [0, 0]
    past_calc_error = [0, 0]
    do_distance = [0, 0]


    try:
        while True:
            time.sleep(0.001)
            img = sc.capture()
            if img is None:
                continue

            cropped_img = crop_for_colorbot(img, target_size=6)
            color_bot.process_image(cropped_img)

            if trigger_button():
            # if True:
                has_target = color_bot.get_result()
                if has_target:
                    mouse.left(1)
                    time.sleep(0.063 + (random.randint(-6,6) / 1000))
                    mouse.left(0)
                    time.sleep(0.192)

            result = det.infer(img, target_class=TARGET)
            if result is not None:
                result[:, :4] = result[:, :4] * GRAB_SIZE / 256
                closest_dist, closest_target = float('inf'), False
                for x1, y1, x2, y2, conf in result:
                    if conf < CONF_T:
                        continue
                    center_x = x1 + (x2 - x1) * POST_X
                    center_y = y1 + (y2 - y1) * POST_Y
                    dist = ((GRAB_SIZE/2 - center_x)**2 + (GRAB_SIZE/2 - center_y)**2)**0.5
                    if dist < closest_dist and dist < RENDER:
                        closest_center_x = center_x
                        closest_center_y = center_y
                        closest_dist = dist
                        closest_target = True
                
                if closest_target:
                    # 計算誤差
                    error_x = (closest_center_x - GRAB_SIZE / 2)
                    error_y = (closest_center_y - GRAB_SIZE / 2)
                    error_calc_x = error_x * VAL_FACTOR
                    error_calc_y = error_y * VAL_FACTOR
                    error = [error_x, error_y]
                    calc_error = [error_calc_x, error_calc_y]
                    if closest_dist > DEAD_Z  and aim_button():
                        # PID 計算
                        for n in range(2):
                            P[n] = calc_error[n] * P_n[n]
                            I[n] = I[n] + calc_error[n] * I_n[n]
                            I[n] = np.sign(I[n]) * min(abs(I[n]), MAX_I[n])
                            D[n] = (((past_calc_error[n] - calc_error[n]) / GRAB_SIZE) * 100) * D_n[n]

                            past_error[n] = error[n]
                            past_calc_error[n] = calc_error[n]
                            if error[n] < close_z:
                                do_distance[n] = P[n]
                            else:
                                do_distance[n] = P[n] + I[n] + D[n]

                            
                        
                        # 如果按下左鍵，垂直不移動
                        if mouse.isdown_left():
                            do_distance[1] = 0
                        
                        # 移動鼠標
                        move_mouse(round(do_distance[0]), round(do_distance[1]))
                        

                    else:
                        # 未檢測到目標時重置所有 PID 變量
                        error = [0, 0]
                        calc_error = [0, 0]
                        past_error = [0, 0]
                        past_calc_error = [0, 0]
                        I = [0, 0]
                        D = [0, 0]
                        do_distance = [0, 0]
                else:
                    error = [0, 0]
                    calc_error = [0, 0]
                    past_error = [0, 0]
                    past_calc_error = [0, 0]
                    I = [0, 0]
                    D = [0, 0]
                    do_distance = [0, 0]
            else:
                error = [0, 0]
                calc_error = [0, 0]
                past_error = [0, 0]
                past_calc_error = [0, 0]
                I = [0, 0]
                D = [0, 0]
                do_distance = [0, 0]
    except KeyboardInterrupt:
        color_bot.stop_detection()
        print("程序已停止")

if __name__ == "__main__":
    mouse = dhzbox.DHZBOX("192.168.8.88", 8888, 88)
    mouse.monitor(1234)
    mouse.mask_all(0)
    mouse.mask_side1(1)
    mouse.mask_side2(1)
    def trigger_button():
        return mouse.isdown_side2()
    def aim_button():
        return mouse.isdown_side1()

    GRAB_SIZE, CONF_T, TARGET = 256, 0.65, 0
    RENDER = 50
    # PID 控制器參數
    SENS = 0.13         # 靈敏度
    P_n = [0.18, 0.18]   # P 增益
    I_n = [0.005, 0.005] # I 增益
    D_n = [0.02 / SENS , 0.02 / SENS]   # D 增益
    MAX_I = [0.5 / SENS, 0.2 / SENS]      # 積分項最大值
    close_z = 3

    DEAD_Z, POST_X, POST_Y = 1.2, 0.50, 0.125

    sc = MJPEG_Reader(ip='192.168.8.170', port=8787, grab_size=GRAB_SIZE)
    sc.start()
    det = Inference()

    main()