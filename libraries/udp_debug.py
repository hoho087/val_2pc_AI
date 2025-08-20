# coding: utf-8
import socket
import threading
import time

class UDPDebugReceiver:
    def __init__(self, port):
        self.port = port
        self.RECEIVER_FLAG = False
        # 初始化状态变量
        self.LEFTSTATE = 0
        self.RIGHTSTATE = 0
        self.MIDDLESTATE = 0
        self.SIDE1STATE = 0
        self.SIDE2STATE = 0
        self.KEYSTATE = ""

    def start_receiver(self):
        """启动接收线程"""
        self.RECEIVER_FLAG = True
        t_receiver = threading.Thread(target=self.debug_udp_receiver, name='debug_receiver', args=())
        t_receiver.daemon = True
        t_receiver.start()
        print(f"调试接收器已启动，监听端口: {self.port}")

    def stop_receiver(self):
        """停止接收线程"""
        self.RECEIVER_FLAG = False
        print("接收器已停止")

    def debug_udp_receiver(self):
        """调试用的 UDP 接收函数"""
        # 创建 UDP 套接字
        try:
            sock_receiver = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            print("UDP 套接字创建成功")
        except Exception as e:
            print(f"创建 UDP 套接字失败: {e}")
            return

        # 尝试绑定端口
        try:
            sock_receiver.bind(("", self.port))
            print(f"成功绑定到端口 {self.port}")
        except Exception as e:
            print(f"端口绑定失败: {e}")
            sock_receiver.close()
            return

        # 设置超时以便优雅退出
        sock_receiver.settimeout(2.0)

        # 接收循环
        while self.RECEIVER_FLAG:
            try:
                print("等待数据包...")
                data, address = sock_receiver.recvfrom(1024)
                print(f"收到来自 {address} 的数据: {data}")
                
                # 尝试解码数据
                try:
                    msg = data.decode('utf-8')
                    print(f"解码后的消息: {msg}")
                    
                    # 解析命令
                    try:
                        cmd = msg.split("|")
                        if len(cmd) >= 6:
                            self.LEFTSTATE = int(cmd[0])
                            self.MIDDLESTATE = int(cmd[1])
                            self.RIGHTSTATE = int(cmd[2])
                            self.SIDE1STATE = int(cmd[3])
                            self.SIDE2STATE = int(cmd[4])
                            self.KEYSTATE = str(cmd[5])
                            print(f"解析结果: Left={self.LEFTSTATE}, Middle={self.MIDDLESTATE}, Right={self.RIGHTSTATE}, "
                                  f"Side1={self.SIDE1STATE}, Side2={self.SIDE2STATE}, Keys={self.KEYSTATE}")
                        else:
                            print("数据格式不完整")
                    except ValueError as e:
                        print(f"数据解析错误: {e}")
                        self.reset_states()
                except UnicodeDecodeError as e:
                    print(f"数据解码失败: {e}")
            except socket.timeout:
                print("接收超时，继续等待...")
            except Exception as e:
                print(f"接收过程中发生错误: {e}")

        sock_receiver.close()
        print("UDP 套接字已关闭")

    def reset_states(self):
        """重置状态"""
        self.LEFTSTATE = 0
        self.RIGHTSTATE = 0
        self.MIDDLESTATE = 0
        self.SIDE1STATE = 0
        self.SIDE2STATE = 0
        self.KEYSTATE = ""
        print("状态已重置")

    def get_states(self):
        """返回当前状态"""
        return (self.LEFTSTATE, self.MIDDLESTATE, self.RIGHTSTATE, 
                self.SIDE1STATE, self.SIDE2STATE, self.KEYSTATE)

if __name__ == "__main__":
    # 测试用例
    debug_receiver = UDPDebugReceiver(8888)  # 使用与 monitor 函数相同的端口
    debug_receiver.start_receiver()

    # 运行一段时间以观察输出
    try:
        while True:
            time.sleep(1)
            states = debug_receiver.get_states()
            print(f"当前状态: Left={states[0]}, Middle={states[1]}, Right={states[2]}, "
                  f"Side1={states[3]}, Side2={states[4]}, Keys={states[5]}")
    except KeyboardInterrupt:
        debug_receiver.stop_receiver()
        print("调试程序已退出")