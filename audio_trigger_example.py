from libraries.audio_trigger import DodgingTrigger
import time
import threading


class Dodging:
    def __init__(self):
        try:
            self.dt = DodgingTrigger(samples_dir="./samples", threshold=0.10, ratio=1.0, is_allowed_succe_dodge=False)
            self.dt.start_listening()
        except Exception as e:
            self.dt.stop_listening()
            raise

        self.running = True
        self.thread = threading.Thread(target=self._dodge_loop, daemon=True)
        self.thread.start()

    def _dodge_loop(self):
        while self.running:
            try:
                need_dodge = self.dt.get_result()
                if need_dodge:
                    print("聲音匹配")
            except Exception as e:
                print(f"闪避循环中发生错误: {e}")
            time.sleep(0.01)

    def stop(self):
        self.running = False
        self.thread.join()
        try:
            self.dt.stop_listening()
        except Exception as e:
            print(f"停止触发器监听失败: {e}")


def main():
    try:
        while True:
            A = "你想做的事"
            time.sleep(1)
    except KeyboardInterrupt:
        dodger.stop()
        print("程序已停止")

if __name__ == "__main__":
    dodger = Dodging()
    main()