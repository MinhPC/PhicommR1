# Loa Phicomm R1 (firmware AI-Box) — Bối cảnh kỹ thuật

Tài liệu này tổng hợp mọi thứ đã tìm hiểu về loa Phicomm R1 của Minh, để dùng làm ngữ cảnh khi chuyển sang project khác. Ngày tổng hợp: 2026-10-24.

**Quy ước độ tin cậy:** mục "Đã xác minh" là thứ đã đo/đọc trực tiếp từ loa. Mục "Chưa xác minh" là suy luận hoặc lấy từ README của dự án bên ngoài, chưa thử trên loa này.

## 1. Thiết bị

| | |
|---|---|
| Loa | Phicomm R1, tên thiết bị `Phicomm_R1_7C0B` |
| IP trong LAN | `192.168.31.143` |
| SoC | Rockchip RK3229 (`ro.board.platform=rk322x`), ABI `armeabi-v7a` |
| Android | 5.1.1 (API 22), build `LMY49F release-keys` |
| Model prop | `rk322x-box` |
| Firmware gốc (`ro.build.version.incremental`) | **3415** |
| Phần mềm trợ lý | **AI-Box / AI Box Plus** (`ver: 1877`, `u_ver: 1000` trong `get_info`; đây là phiên bản app, không phải firmware gốc) |
| Mã thiết bị | `device_udid` có trong `get_info` |
| Mạng | Wi-Fi 2.4 GHz; ping tới loa 11–107 ms, mất gói 0% |

**Lưu ý sửa sai:** chip R1 là **RK3229**, KHÔNG phải Amlogic S905D (S905D là của hộp Phicomm N1). Các bản Armbian/OpenWrt cho N1 không dùng được cho R1.

HA server của Minh ở `192.168.31.72:8123`, chạy HTTPS với chứng chỉ chỉ hợp lệ cho `holoto.duckdns.org` (hết hạn 2026-12-10). Gọi bằng IP sẽ lệch tên chứng chỉ.

## 2. Các cổng trên loa (đã xác minh)

| Cổng | Dịch vụ | Ghi chú |
|---|---|---|
| 8081 | HTTP, trang web điều khiển "AI BOX" (Tailwind, Live2D) | Phục vụ `js/*.js` không cần đăng nhập |
| 8080 | WebSocket điều khiển loa (`SpeakerConnection`) | JSON `{"type": ...}` |
| 8082 | WebSocket AI-Box Plus (`AiboxPlusConnection`) | JSON `{"action": ...}` |
| 8088 | Control panel của client kuteo-git/db-robot | Chỉ khi cài client đó; chưa kiểm tra trên loa này |
| 5555 | ADB mạng | **Chưa xác minh** có bật hay không |

Không có xác thực ở bất kỳ cổng nào trong số trên.

## 3. Giao thức WebSocket cổng 8080 (type-based)

Gửi `{"type": "get_info"}` → phản hồi `{"msg":"ok","type":"get_info","code":200,"data":"<chuỗi JSON>"}` (`data` là JSON lồng nhau dạng chuỗi, phải `json.loads` lần nữa).

Trường chính trong `get_info.data`: `vol` (0–15), `play_state` (bool), `mute` (bool), `device_name`, `device_udid`, `ver`, `dlna_open` (true), `play_mode`, `PlayerType`, `ttsModelType` (`SWEET`), `music_light_*`, `airplay_open`.

Lệnh đã **đọc từ mã giao diện** (đã thử thực tế chỉ `get_info` và `get_eq_config`):

| Mục đích | Payload |
|---|---|
| Đặt âm lượng | `{"type":"set_vol","vol":N}` rồi `{"type":"send_message","what":4,"arg1":5,"arg2":N}` |
| Phát | `{"type":"send_message","what":4,"arg1":3,"arg2":-1}` |
| Tạm dừng | `{"type":"send_message","what":4,"arg1":2,"arg2":-1}` |
| Bài kế | `{"type":"send_message","what":65536,"arg1":0,"arg2":1,"obj":"web_next"}` + `{"type":"next"}` |
| Bài trước | tương tự với `web_prev` + `{"type":"prev"}` |
| Chế độ phát | `{"type":"set_play_mode","mode":1|2}` (1 shuffle, 2 repeat) |
| Bật/tắt DLNA, AirPlay | `Set_DLNA_Open`, `Set_AirPlay_Open` |
| EQ | `get_eq_config` (đã thử đọc được) |
| Shell | `{"type":"shell","type_id":"myshell","shell":"<lệnh>"}` → phản hồi `type: "shell"` |

Kênh `shell` chạy lệnh tùy ý trên loa. Mình đã dùng nó chỉ để chạy `getprop` (đọc). Lệnh ghi/đổi hệ thống cần Minh đồng ý rõ ràng.

Chưa tìm ra lệnh tắt tiếng (loa có báo `mute` nhưng không thấy lệnh đặt).

## 4. Giao thức WebSocket cổng 8082 (action-based)

Các `action` thấy trong mã: `chat_get_state`, `chat_get_history`, `chat_send_text` (`{"text": ...}`), `chat_wake_up`, `chat_test_mic`, `ota_get`, `ota_set` (`{"ota_url": ...}`), `hass_get`, `hass_set`, `hass_pipelines_get`, `pause`/`resume`/`stop`/`next`/`previous`/`seek`, `alarm_*`, `playlist_*`, `search_songs`/`search_zing`/`play_zing`, `wifi_*`, `wake_word_*`, `get_version`, `get_premium`, nhiều thứ khác.

Phản hồi có `type` như `wake_word_sensitivity_state`, `wake_word_window_state`, `wake_word_enabled_state`, `hass_config`, `ota_config`, `chat_message`, `stereo_get_state_result`, `led_state`.

Cấu hình đọc được (đã xác minh, **token Home Assistant luôn bị che, không được in ra**):
- `hass_config`: URL `https://192.168.31.72:8123/`, `agent_id` = `conversation.google_ai_conversation`, `pipeline_name` = "-- Mặc định --", `configured: true`.
- `ota_config`: `https://api.tenclass.net/xiaozhi/ota/`; các lựa chọn: `https://api.tenclass.net/xiaozhi/ota/`, `https://me.ai-box.vn/xiaozhi/ota/`, `home_assistant`.
- Wake word: bật, độ nhạy 0.90, cửa sổ 5 (giới hạn 5–7).

## 5. Wake word

Cố định là **"Ô Kê Na Bu"** (OK Nabu). Firmware AI-Box chỉ cho bật/tắt, chỉnh độ nhạy và cửa sổ nhận diện. **Không có lệnh đổi từ khóa.** Có nút "Wake Up" (`chat_wake_up`) để kích hoạt bằng tay.

Client khác (chưa thử): kuteo-git/db-robot cho chọn Snowboy "Alexa", microWakeWord "OK Nabu", hoặc "Nabi ơi" (thử nghiệm); shj4588 đổi sang "小智小智".

## 6. Tích hợp Home Assistant đã viết

Thư mục `custom_components/phicomm_r1/` (trong repo HomeAssistant, **chưa commit, chưa cài lên HA**):
- Config flow (IP + cổng 8080), một thực thể `media_player` (phát/tạm dừng/bài kế/bài trước/âm lượng, trạng thái, âm lượng 0–15 quy về 0–1, tắt tiếng chỉ đọc).
- Cập nhật mỗi 5 giây qua kết nối WebSocket ngắn; client trong `api.py`.
- Đã kiểm tra: biên dịch được và `get_info` đọc đúng loa thật. **Chưa thử:** các lệnh điều khiển, chạy trong HA thật.
- Phát nhạc/TTS: dùng tích hợp **DLNA Digital Media Renderer** có sẵn của HA (loa báo `dlna_open: true`); chưa thử.

## 7. Sự cố đang theo dõi: chat AI "lúc được lúc không"

Triệu chứng (Minh xác nhận): cả lệnh nhà thông minh lẫn chat thường đều có lúc không phản hồi; tin của Minh vẫn hiện trong khung chat, nhưng lịch sử cho thấy những tin đó **không gửi lên được máy chủ**. ESP32 của Minh dùng cùng máy chủ (`api.tenclass.net`) vẫn phản hồi tốt.

Đã đo: `api.tenclass.net/xiaozhi/ota/` và `me.ai-box.vn/xiaozhi/ota/` từ PC của Minh đều trả `200` 6/6 lần (0,25–0,8 s). Phép đo này chỉ thử HTTP OTA, không thử WebSocket lâu dài.

Kết luận hiện tại: vấn đề nhiều khả năng nằm ở **phía R1** (Wi-Fi yếu, hoặc app AI-Box không giữ/nối lại WebSocket tốt), không phải máy chủ. Chưa chứng minh.

Phát hiện riêng cho lệnh nhà thông minh: loa gọi HA bằng IP (`https://192.168.31.72:8123/`) trong khi chứng chỉ chỉ hợp lệ cho `holoto.duckdns.org`; agent `conversation.google_ai_conversation` có thể không tồn tại (repo có `deepseek_conversation`). Router không NAT loopback port 8123 nên dùng tên miền trong LAN có thể không được. Chưa kiểm tra phía loa.

## 8. Phương án firmware / client (đã tìm hiểu, chưa cài)

Không có dự án nào build **ảnh firmware đầy đủ** cho R1. Tất cả là APK trên Android gốc. Mã nguồn của AI-Box Plus **không tìm thấy** (có vẻ đóng).

| Dự án | Loại | Điểm đáng chú ý |
|---|---|---|
| `kuteo-git/xiaozhi-android` + `kuteo-git/robot-esp32` | APK client mỏng + server | **Chỉ kết nối khi wake word kích hoạt**; panel cổng 8088; build JDK 17, SDK 35, NDK 27, CMake 3.22.1, minSdk 22; không có AEC; chưa thấy giấy phép; hai đầu phải khớp sample rate/số kênh (robot-esp32 mẫu: 48000/2) |
| `hoanglt1223/db-robot-phincomR1` (nhánh của `ledienbien-ai`) | APK đầy đủ, UI tiếng Việt | Chọn wake word; keystore công khai; trình cài kiểu `curl \| bash`; mặc định dùng `sv1.dbrobot.vn` |
| `shj4588/Phicomm_R1_XiaoZhi_Client` | 3 APK vá vào tiến trình giọng nói gốc | Giữ xử lý 4 micro (AEC, beamforming); **bắt buộc firmware gốc đúng 3448** (loa này là **3415**); console cổng 8080 không xác thực; không giấy phép; wake word "小智小智" |
| `xuan2261/r1-xiaozhi` | APK đơn giản, MIT | Wake word chỉ phát hiện theo năng lượng; nhiều file sửa lỗi |
| `cyberty/R1up4Mac` | Script nâng cấp firmware gốc qua ADB | Có bước `3415 → 3448` (mục 6); đẩy `otaprop.txt` rồi reboot; cảnh báo không cắt nguồn; chưa kiểm tra nội dung OTA |

Cách cài chung (theo README, chưa thử): `adb connect <IP>:5555`, `adb push <apk> /data/local/tmp/`, `adb shell pm install -r ...`. Chưa rõ cách bật `adbd` cổng 5555 lần đầu.

Server Xiaozhi tự host có sẵn trong repo: thư mục `xiaozhi/` (add-on HAOS, ASR/LLM/TTS qua API cloud, điều khiển HA qua `ha_devices`). **Chưa chạy thực tế** (xem `xiaozhi/NOTES.md`); chưa biết app Xiaozhi trên R1 nhập địa chỉ OTA ở đâu.

## 9. Rủi ro và quy tắc

- Đa số dự án trên không có giấy phép rõ ràng hoặc ghi "chỉ nghiên cứu".
- Nhiều trình cài chạy script tải từ mạng (`curl | bash`, `wget | sh` từ tên miền lạ). Phải đọc script trước khi chạy.
- Panel/console trên loa (8080/8081/8082/8088) **không có xác thực**; ai trong LAN cũng điều khiển được.
- Cài client mới có thể phải ẩn gói gốc (`pm hide`, đảo ngược bằng `pm enable`); ghi lại gói đã ẩn.
- Không cắt nguồn khi nâng cấp firmware.
- Giữ nguyên AI-Box để dự phòng trước khi thử client khác.
- **Quyền:** lệnh `ota_set` (đổi máy chủ OTA) đã bị trình phân loại quyền của Claude Code chặn; chưa thực hiện. Muốn thay đổi cấu hình loa qua WebSocket/shell, Minh cần cho phép rõ ràng hoặc tự làm trên giao diện `http://192.168.31.143:8081`.
- Không in token HA hay API key ra màn hình; che trước khi hiển thị.

## 10. Việc còn dang dở / gợi ý tiếp theo

1. Cài `custom_components/phicomm_r1/` lên HA và thử các lệnh điều khiển (hỏi Minh trước khi gửi lệnh gây ra tiếng).
2. Đổi OTA sang `https://me.ai-box.vn/xiaozhi/ota/` (Minh tự làm trên giao diện loa hoặc cấp quyền) để so sánh độ ổn định.
3. Sửa URL/agent HA trên loa (tên miền thay IP, Agent ID đúng) nếu muốn lệnh nhà thông minh ổn định.
4. Thử client kuteo-git hoặc db-robot với server Xiaozhi trong LAN (add-on `xiaozhi/` hoặc robot-esp32); kiểm tra khớp định dạng âm thanh.
5. Nếu cần chất lượng thu âm tốt hơn: cân nhắc shj4588, sau khi nâng firmware lên 3448 bằng R1up4Mac (rủi ro, cần cẩn trọng).
6. Cân nhắc dùng ESP32 làm loa trợ lý chính (Minh nói ESP32 phản hồi tốt), R1 chỉ làm loa phát qua DLNA.
7. Có thể thêm dịch vụ "wake up" (`chat_wake_up`) vào tích hợp HA.
