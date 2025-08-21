# val_2pc_AI
基於yolo使用udp通訊圖像識別遊戲自動化操作
# 簡介
為了解決性能影響與檢測的一個項目，使用obs自帶的功能通訊  
需使用kmbox或dhzbox硬件操控，或替換為你自己的數標模擬方式  
我並沒有kmbox net，因此val_ai_obs_kmnet是否正常運行我無法保證  
同時我基於[mouse_control](https://github.com/suixin1424/mouse_control)訓練了一份神經網絡模型，在net_mouse_control_example可以看到使用方法，如果有需要可以將其加入至代碼實現中  
本項目自帶一個AI模型，放置於libraries  
libraries裡的audio_trigger使用最大歸一化交叉相關匹配特徵音頻波形，原本是嘗試用來自動閃避(閃光)的，但抗干擾性似乎不夠，就把功能剃除了。  
但是保留了audio_trigger_example的文件，你可以在裡面看到使用方法，如果有需要可以將功能放到需要的地方  
# 使用方法
將主機與副機連至同一局域網內  
dll文件夾內為kmbox的庫和可能缺失的dll，請將其移動至你的虛擬環境內  
val_ai_obs_dhz、val_ai_obs_kmnet，各自為dhz和kmbox net的硬件調用版本，根據你擁有的硬件自行選擇使用  
開啟obs studio:  
+ 將設置中的輸出分辨率調整至256(與模型輸入大小相同)  
+ 添加一個顯示器採集(盡量使用dxgi)，使用濾鏡功能中的裁剪，將顯示器採集畫面與輸出分辨率同步並對其畫面中央  
+ 進入設置->輸出->錄製  
  + 類型改成自定義輸出  
  + 輸出類型改成輸出到url  
  + url填寫udp://副機的局域網ip:自訂義端口  
  + 格式選擇mjpeg  
  + 碼率在盡量不影響性能和延遲的情況下調高，通常至少需要10000kbps  
  + 關鍵幀設置0  
  + 隨後確定

開啟val_ai_obs_dhz或val_ai_obs_kmnet
+ if __name__ == "__main__":下的參數為簡易自定義參數  
  + 將你自己的硬件填入硬件調用初始化部分(kmbox net可於硬件上的小顯示器找到)  
  + monitor為硬件通訊使用的端口，可自訂  
  + 將MJPEG_Reader的ip與port設置為你剛才於obs瑱入的ip與port
  + 接下來只需將SENS調整為你的SENS就可以使用
  + 可以自行調整pid參數來滿足想要的效果  
