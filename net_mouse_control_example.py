import numpy as np
from collections import deque
import torch
from cv2 import dnn
import time
def main():
    net = dnn.readNetFromONNX("mouse.onnx")
    move = [20,5]
    input_data = np.array([[move[0], move[1]]], dtype=np.float32)
    net.setInput(input_data)
    output = net.forward()
    absolute_coords = output.reshape(-1, 2)
    # 轉換為 torch 張量並計算相對座標
    absolute_points = torch.from_numpy(absolute_coords[:10]).float()
    relative_points = torch.diff(absolute_points, dim=0, prepend=absolute_points[:1])
    # 提取座標
    coords = relative_points.tolist()
    for i, (rx, ry) in enumerate(coords, 1):
        print(rx, ry)

if __name__ == "__main__":
    main()