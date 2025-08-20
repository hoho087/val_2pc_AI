"""
DHZBOX_LITE的调用例子（以太网）

你可以直接把源码内嵌到你的项目中，代码写得有点烂
如果有更好的改进请联系我~~ 栓Q~~

Author:大胡子电竞
Date:2025/01/25
"""
# coding: utf-8
# cython: language_level=3
import socket
import threading
import time

class DHZBOX:
    def __init__(self, IP, PORT, RANDOM):
        # 初始化参数
        self.IP = IP
        self.PORT = PORT
        self.RANDOM = RANDOM

        # 鼠标状态
        self.LEFTSTATE = 0
        self.RIGHTSTATE = 0
        self.MIDDLESTATE = 0
        self.SIDE1STATE = 0
        self.SIDE2STATE = 0
        self.KEYSTATE=""

        # 标志位
        self.RECEIVER_FLAG = False

    def __encrypt_string(self, str):
        # 加密函数
        # 传入字符串，和密钥，返回加密后的字符串
        key = self.RANDOM
        encrypted_string = []
        for char in str:
            if char.isalpha():
                if char.islower():
                    new_char = chr((ord(char) - ord('a') + key) % 26 + ord('a'))
                elif char.isupper():
                    new_char = chr((ord(char) - ord('A') + key) % 26 + ord('A'))
                encrypted_string.append(new_char)
            else:
                encrypted_string.append(char)
        return ''.join(encrypted_string)


    def __udp_sender(self, message):
        SCOK_sender = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            SCOK_sender.sendto(message.encode(), (self.IP, self.PORT))
            SCOK_sender.settimeout(0.1)
            try:
                relpy,_=SCOK_sender.recvfrom(1024)
                # print(f'收到回码{relpy}')
            except socket.timeout:
                # print('回码超时,重发')
                self.__udp_sender(message)

        finally:
            SCOK_sender.close()

    def __udp_receiver(self, port):
        SCOK_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        SCOK_receiver.bind(("", port))
        while self.RECEIVER_FLAG:
            data, address = SCOK_receiver.recvfrom(1024)
            mag = data.decode()
            try:
                cmd = mag.split("|")
                self.LEFTSTATE = int(cmd[0])
                self.MIDDLESTATE = int(cmd[1])
                self.RIGHTSTATE = int(cmd[2])
                self.SIDE1STATE = int(cmd[3])
                self.SIDE2STATE = int(cmd[4])
                self.KEYSTATE=str(cmd[5])
            except:
                self.LEFTSTATE, self.RIGHTSTATE, self.MIDDLESTATE, self.SIDE1STATE, self.SIDE2STATE ,self.KEYSTATE= 0, 0, 0, 0, 0,""

    """控制类函数"""

    def move(self, x, y):
        cmd = self.__encrypt_string(f"move({int(x)},{int(y)})")
        self.__udp_sender(cmd)

    def left(self, state):
        cmd = self.__encrypt_string(f"left({int(state)})")
        self.__udp_sender(cmd)

    def right(self, state):
        cmd = self.__encrypt_string(f"right({int(state)})")
        self.__udp_sender(cmd)

    def middle(self, state):
        cmd = self.__encrypt_string(f"middle({int(state)})")
        self.__udp_sender(cmd)

    def wheel(self, state):
        cmd = self.__encrypt_string(f"wheel({int(state)})")
        self.__udp_sender(cmd)

    def mouse(self, button, x, y, w):
        cmd = self.__encrypt_string(f"mouse({int(button)},{int(x)},{int(y)},{int(w)})")
        self.__udp_sender(cmd)

    def side1(self,state):
        cmd = self.__encrypt_string(f"side1({int(state)})")
        self.__udp_sender(cmd)

    def side2(self,state):
        cmd = self.__encrypt_string(f"side2({int(state)})")
        self.__udp_sender(cmd)

    def keydown(self,key):
        cmd=self.__encrypt_string(f"keydown({key})")
        self.__udp_sender(cmd)

    def keyup(self,key):
        cmd = self.__encrypt_string(f"keyup({key})")
        self.__udp_sender(cmd)


    """监视"""
    def monitor(self, port):
        if port == 0:
            cmd = self.__encrypt_string(f"monitor(0)")
            self.__udp_sender(cmd)
            self.RECEIVER_FLAG = False
            time.sleep(0.5)
        elif abs(port) > 0:
            cmd = self.__encrypt_string(f"monitor({int(port)})")
            self.__udp_sender(cmd)
            self.RECEIVER_FLAG = True
            t_receiver = threading.Thread(target=self.__udp_receiver, name='t_receiver', args=(port,))
            t_receiver.daemon = True
            t_receiver.start()

    def isdown_left(self):
        return self.LEFTSTATE

    def isdown_middle(self):
        return self.MIDDLESTATE

    def isdown_right(self):
        return self.RIGHTSTATE

    def isdown_side1(self):
        return self.SIDE1STATE

    def isdown_side2(self):
        return self.SIDE2STATE

    def isdown(self):
        #返回当前所有摁下的热键，如果查询某键是否摁下，请参考以下筛选条件
        return self.KEYSTATE

    def isdown2(self,key):
        #key为字符串，如：'KEY_A' ，键名详见文档附录
        if key in self.KEYSTATE:
            return 1
        else:
            return 0

    """屏蔽类函数"""
    def mask_left(self,state):
        cmd = self.__encrypt_string(f"mask_left({int(state)})")
        self.__udp_sender(cmd)

    def mask_right(self,state):
        cmd = self.__encrypt_string(f"mask_right({int(state)})")
        self.__udp_sender(cmd)

    def mask_middle(self,state):
        cmd = self.__encrypt_string(f"mask_middle({int(state)})")
        self.__udp_sender(cmd)

    def mask_wheel(self,state):
        cmd = self.__encrypt_string(f"mask_wheel({int(state)})")
        self.__udp_sender(cmd)

    def mask_side1(self,state):
        cmd = self.__encrypt_string(f"mask_side1({int(state)})")
        self.__udp_sender(cmd)

    def mask_side2(self,state):
        cmd = self.__encrypt_string(f"mask_side2({int(state)})")
        self.__udp_sender(cmd)

    def mask_x(self,state):
        cmd = self.__encrypt_string(f"mask_x({int(state)})")
        self.__udp_sender(cmd)

    def mask_y(self,state):
        cmd = self.__encrypt_string(f"mask_y({int(state)})")
        self.__udp_sender(cmd)

    def mask_all(self,state):
        cmd = self.__encrypt_string(f"mask_all({int(state)})")
        self.__udp_sender(cmd)

    def mask_keyboard(self,key):
        cmd=self.__encrypt_string(f"mask_keyboard({str(key)})")
        self.__udp_sender(cmd)

    def dismask_keyboard(self,key):
        cmd=self.__encrypt_string(f"dismask_keyboard({str(key)})")
        self.__udp_sender(cmd)

    def mask_keyboard_all(self):
        cmd=self.__encrypt_string(f"dismask_keyboard_all()")
        self.__udp_sender(cmd)

if __name__ == '__main__':
    
    # 测试用例
    mouse = DHZBOX("192.168.8.88", 8888, 88)

    mouse.monitor(9527)
    print(f"左狀態: {mouse.LEFTSTATE}")

    #移动
    while True:
        # print(mouse.isdown_side2())
        print(f"左狀態: {mouse.LEFTSTATE}")
        time.sleep(0.1)

    #左键控制
    #mouse.left(1)
    #time.sleep(0.1)
    # mouse.left(0)
    # #右键控制
    # mouse.right(1)
    # time.sleep(0.1)
    # mouse.right(0)
    # #滚轮控制
    # mouse.wheel(2)
    # #组合控制
    # #摁下右键 并且下移10个单位 并且滚动滚轮
    # mouse.mouse(4,0,10,2)

    # #点击A键
    #mouse.keydown('KEY_A')
    #time.sleep(0.1)
    #mouse.keyup('KEY_A')

    # # 屏蔽左键
    #mouse.mask_left(0)
    # # 屏蔽右键
    # mouse.mask_right(1)
    # # 屏蔽中键
    # mouse.mask_middle(1)
    # # 屏蔽滚轮
    # # 屏蔽X轴
    # mouse.mask_x(1)
    # # 屏蔽Y轴
    # mouse.mask_y(1)
    # # 全部屏蔽
    # mouse.mask_all(1)
    #屏蔽键盘A键
    #mouse.mask_keyboard('KEY_A')
    # 解除屏蔽A键
    #mouse.dismask_keyboard('KEY_A')
    # 解除屏蔽所有键
    # mouse.dismask_keyboard_all()



    # # 开启监听
    # mouse.monitor(10086)
    # while True:
    #      time.sleep(0.001)
    #      print(mouse.isdown_left(),mouse.isdown_middle(),mouse.isdown_right(),mouse.isdown_side1(),mouse.isdown_side2(),mouse.isdown())
    #     # print(f'物理左键的状态为：{mouse.isdown_left()}')
    #     # print(f'物理中键的状态为：{mouse.isdown_middle()}')
    #     # print(f'物理右键的状态为：{mouse.isdown_right()}')
    #     # print(f'物理侧键1的状态为：{mouse.isdown_side1()}')
    #     # print(f'物理侧键2的状态为：{mouse.isdown_side2()}')
    #     # print(f'摁下的热键：{mouse.mouse.isdown()}')