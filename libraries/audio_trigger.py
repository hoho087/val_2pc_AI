import multiprocessing
import threading
import time
import numpy as np
import librosa
import soundcard as sc  
from scipy.signal import correlate, butter, filtfilt  
from sklearn.preprocessing import scale  
import warnings  
from soundcard.mediafoundation import SoundcardRuntimeWarning 
import os  
import queue  


warnings.filterwarnings('ignore', category=SoundcardRuntimeWarning)

# 配置参数
SAMPLES_DIR = "./samples"  # 特征音频所在的子目录路径
THRESHOLD = 0.1  # 触发阈值，当NCC分数超过此值时触发动作
EXPANSION_RATIO = 1.0  # 最大NCC系数扩展比例，用于调整匹配灵敏度
IS_ALLOW_SUCCESSIVE_TRIGGER = False  # 是否允许连续触发，False表示每次触发后需等待分数低于阈值

class GameAudioListener:
    """
    游戏音频监听器类，用于实时捕获系统音频并与特征音频进行匹配
    """
    used_sr = 32000  # 采样率，单位Hz
    used_channel = 2  # 声道数，立体声为2
    chunk_size = 1600  # 每次处理的音频块大小，单位采样点
    device_index = 0  # 音频设备编号，默认使用第一个设备
    sample_len = 0.2  # 每次采样时长，单位秒
    degree = 4  # 巴特沃斯滤波器阶数
    cut_off = 1000  # 截止频率，单位Hz，用于去除低频噪声

    def __init__(self, samples_dir: str, ratio=1.0):
        """
        初始化音频监听器，加载特征音频并设置滤波器
        
        参数:
            samples_dir (str): 特征音频文件所在目录路径
            ratio (float): NCC系数扩展比例，默认1.0
        """
        self.sample_waveforms = {}
        if not os.path.exists(samples_dir):
            raise FileNotFoundError(f"目录 {samples_dir} 不存在，请创建并放入特征音频文件")
        
        for wav_file in os.listdir(samples_dir):
            if wav_file.endswith(".wav"):
                wav_path = os.path.join(samples_dir, wav_file)
                waveform, sample_rate = librosa.load(wav_path)
                waveform = librosa.resample(waveform, orig_sr=sample_rate, target_sr=self.used_sr)
                self.sample_waveforms[wav_file] = waveform
        
        if not self.sample_waveforms:
            raise ValueError(f"目录 {samples_dir} 中没有找到任何 .wav 文件")
        
        self.b, self.a = butter(self.degree, self.cut_off, btype='highpass', output='ba', fs=self.used_sr)
        for key in self.sample_waveforms:
            self.sample_waveforms[key] = self._filtering(self.sample_waveforms[key])
        
        loopback_speaker = sc.get_microphone(id=str(sc.default_speaker().name), include_loopback=True)
        self.audio_instance = loopback_speaker.recorder(samplerate=self.used_sr, channels=self.used_channel)
        
        self.ratio = ratio
        print("初始化完毕，发现以下特征音频：", list(self.sample_waveforms.keys()))

    def _filtering(self, _waveform: np.ndarray):
        """对音频波形应用零相位滤波，去除低频噪声"""
        return filtfilt(self.b, self.a, _waveform)

    def matching(self, stream_waveform: np.ndarray):
        """计算输入音频与特征音频的NCC，返回最高分数和匹配文件名"""
        stream_waveform = self._filtering(stream_waveform)
        norm_stream_waveform = scale(stream_waveform, with_mean=False)
        
        max_score = -np.inf
        matched_file = None
        
        for wav_file, sample_waveform in self.sample_waveforms.items():
            norm_sample_waveform = scale(sample_waveform, with_mean=False)
            if norm_stream_waveform.shape[0] > norm_sample_waveform.shape[0]:
                correlation = correlate(norm_stream_waveform, norm_sample_waveform, mode='same', method='fft') / norm_stream_waveform.shape[0]
            else:
                correlation = correlate(norm_sample_waveform, norm_stream_waveform, mode='same', method='fft') / norm_sample_waveform.shape[0]
            current_max = np.max(correlation) * self.ratio
            if current_max > max_score:
                max_score = current_max
                matched_file = wav_file
        
        return max_score, matched_file

class DodgingTrigger(GameAudioListener):
    """
    触发类，在后台持续监听并通过队列返回是否
    """
    def __init__(self, samples_dir: str, threshold=0.1, ratio=1.0, is_allowed_succe_dodge=False):
        """
        初始化触发器
        
        参数:
            samples_dir (str): 特征音频目录路径
            threshold (float): 触发阈值，默认0.1
            ratio (float): NCC扩展比例，默认1.0
            is_allowed_succe_dodge (bool): 是否允许连续触发，默认False
        """
        super().__init__(samples_dir, ratio)
        self.threshold = threshold
        self.is_allowed_succe_dodge = is_allowed_succe_dodge
        self.result_queue = queue.Queue()  # 用于传递监听结果的队列
        self.last_frames = np.empty(shape=(0,), dtype=np.float64)  # 上一次的音频帧
        self.is_not_past_triggered = True  # 是否可以触发，防止重复触发
        self.running = False  # 控制监听线程的标志
        self.listen_thread = None  # 监听线程

    def start_listening(self):
        """启动后台监听线程"""
        if not self.running:
            self.running = True
            self.listen_thread = threading.Thread(target=self._listen_loop, daemon=True)
            self.listen_thread.start()
            print("后台监听已启动")

    def stop_listening(self):
        """停止后台监听线程"""
        if self.running:
            self.running = False
            self.listen_thread.join()
            print("后台监听已停止")

    def _listen_loop(self):
        """后台监听循环"""
        with self.audio_instance as audio_recorder:
            while self.running:
                current_frame = np.empty(shape=(0,), dtype=np.float64)
                for _ in range(int(self.used_sr / self.chunk_size * self.sample_len)):
                    stream_data = audio_recorder.record(numframes=self.chunk_size)
                    read_chunks = librosa.to_mono(stream_data.T)
                    current_frame = np.append(current_frame, read_chunks)

                combined_frames = np.append(self.last_frames, current_frame)
                max_score, matched_file = self.matching(combined_frames)

                # 判断是否需要触发
                need_space = False
                if max_score >= self.threshold:
                    if self.is_not_past_triggered or self.is_allowed_succe_dodge:
                        need_space = True
                        self.is_not_past_triggered = False
                else:
                    self.is_not_past_triggered = True

                self.last_frames = current_frame  # 更新上一帧数据
                self.result_queue.put(need_space)  # 将结果放入队列

    def get_result(self) -> bool:
        """
        获取最新的监听结果
        
        返回:
            bool: True 表示需要按空格键，False 表示不需要
        """
        try:
            return self.result_queue.get_nowait()  # 非阻塞获取队列中的最新结果
        except queue.Empty:
            return False  # 如果队列为空，返回 False

if __name__ == "__main__":
    multiprocessing.freeze_support()
    dt = DodgingTrigger(SAMPLES_DIR, threshold=THRESHOLD, ratio=EXPANSION_RATIO,
                        is_allowed_succe_dodge=IS_ALLOW_SUCCESSIVE_TRIGGER)
    dt.start_listening()  # 启动后台监听
    try:
        while True:
            need_space = dt.get_result()
            print(f"是否需要按空格键，代碼一開始是寫的空格但實際實現不一定要是就是了: {need_space}")
            time.sleep(0.1)  # 控制查询频率
    except KeyboardInterrupt:

        dt.stop_listening()  # 停止监听
