# Gia sư tiếng Anh cho trẻ trên loa Phicomm R1 — Spec và bối cảnh kỹ thuật

Cập nhật: 2026-10-25. Tài liệu gộp hai phần:
- **Phần A** — spec dự án gia sư tiếng Anh (giữ nguyên ý của Minh; chỗ nào lệch với thực tế đã đo thì có khối `⚠` ngay bên dưới).
- **Phần B** — bối cảnh kỹ thuật loa R1, cập nhật bằng các phép đo/thử nghiệm ngày 2026-10-24.

**Quy ước độ tin cậy:** "Đã xác minh" = đã đo/đọc/chạy trực tiếp trên loa hoặc PC của Minh. "Chưa xác minh" = suy luận hoặc lấy từ README/tài liệu bên ngoài. "Giả thuyết" = có dấu hiệu nhưng chưa chứng minh.

---

# PHẦN A — SPEC GIA SƯ TIẾNG ANH

## A1. Tổng quan

Xây một gia sư tiếng Anh bằng giọng nói cho **hai bé trai sinh đôi 8 tuổi (lớp 3) có trình độ khác nhau**. Mỗi bé dùng một thiết bị riêng: loa **Phicomm R1** (client xiaozhi) và board **ESP32-S3 có màn hình LCD** (firmware xiaozhi). Mỗi thiết bị gắn với hồ sơ một bé, nên tiến độ, độ khó và báo cáo của hai bé tách biệt. Backend là bản fork của **xiaozhi-esp32-server** (Python, repo xinnan-tech), chạy trên **PC Windows bằng Docker** trong mạng LAN.

Mục tiêu theo thứ tự ưu tiên:
1. **Phản hồi nhanh** — từ lúc bé nói xong đến lúc loa phát âm thanh đầu tiên ≤ 1,5 s (Tier 1), ≤ 1 s (Tier 3).
2. **Tự nhiên** — câu ngắn, giọng ấm, hỏi lại để bé nói tiếp, không giảng bài dài.
3. **Chi phí thấp** — mục tiêu Tier 1+2 < 2 USD/tháng; Tier 3 có trần chi tiêu cứng.
4. **Đúng chương trình** — dạy theo unit của sách giáo khoa lớp 3 bé đang học.

## A2. Điểm lệch giữa spec và thực tế đã đo (đọc trước khi làm)

Các mục dưới đây đến từ thử nghiệm trên loa/PC của Minh ngày 2026-10-24. Spec gốc chưa tính đến chúng.

1. **Client R1 gốc KHÔNG nối được server chỉ trả WebSocket.** Đã xác minh: khi trỏ OTA của app AI-Box sang server xiaozhi tự host (chỉ có `websocket` trong phản hồi OTA, không có `mqtt`), app dừng ở `ActivationActivity` và chat chết hẳn (không có phản hồi). Mã app có chuỗi `Device activated! Server returned MQTT config`, tức app coi thiết bị là "đã kích hoạt" chỉ khi OTA trả cấu hình MQTT. Đã hoàn tác. → Ràng buộc "**Không sửa client R1**" và "R1 trỏ OTA về `http://<IP_PC>:8003/...`" **không thực hiện được nguyên trạng**. Các hướng (Minh quyết định):
   - (a) **Thay client** bằng `kuteo-git/xiaozhi-android`: đã build từ mã nguồn, cài lên R1 và chạy thật với server xinnan qua WebSocket (xem B9). Đã gỡ sau thử nghiệm.
   - (b) Dựng **gateway MQTT + UDP** cho xiaozhi-esp32-server để giữ app gốc (chưa thử; phần UDP chính là chỗ app gốc gặp lỗi mất phản hồi, xem B7).
   - (c) Để R1 chỉ làm loa phát (truyện/DLNA) và dùng ESP32 làm thiết bị hội thoại.
2. **Client kuteo chỉ kết nối WebSocket sau wake word** (README, "connect-on-wake") nên server không đẩy được âm thanh khi R1 đang chờ → **Story time hẹn giờ phải qua Home Assistant nhắc**, không phải server chủ động phát. Với app gốc (MQTT) chưa rõ; chưa xác minh.
3. **Device ID.** Đã xác minh với client kuteo: header WebSocket `device-id` dạng MAC (client tự sinh, ví dụ `32:83:a0:82:68:c4`, KHÁC MAC thật của loa `fc:7c:02:57:7c:0b`), `client-id` là UUID, `protocol-version: 1`, `Authorization: Bearer test-token` khi không có token; `hello` khai báo `opus` 48000 Hz. Với app gốc, OTA dùng MAC thật `fc:7c:02:57:7c:0b` và **UUID đổi mỗi lần khởi động app** → **khóa theo MAC/`device-id`, không khóa theo UUID.** ESP32 chưa kiểm tra.
4. **SenseVoice không hỗ trợ tiếng Việt.** Cấu hình upstream ghi mô hình `sense-voice-zh-en-ja-ko-yue`. Spec muốn "auto, bé nói lẫn Việt–Anh" → phần tiếng Việt có thể bị nhận dạng sai. Cần thử trước, hoặc dùng ASR khác cho tiếng Việt. (Chưa thử SenseVoice thật trên giọng bé.)
5. **Edge TTS không ổn định.** Trong thử nghiệm trên server xinnan 0.9.7: bản `edge_tts 7.2.6` (ghim trong requirements) bị Microsoft trả **HTTP 403**; nâng lên `7.3.1` thì chạy, nhưng vẫn có **3/15 câu** lỗi `No audio was received` (server thử lại 4–5 lần rồi bỏ → loa im lặng). Spec dùng `en-US-AnaNeural`: cần cơ chế thử lại/dự phòng TTS (chưa thử với giọng tiếng Anh).
6. **Server tự đóng phiên sau 120 s không có tiếng** (`close_connection_no_voice_time: 120`, kèm câu tạm biệt từ `end_prompt`). Client báo `EPIPE` rồi nối lại ở lần sau. Với bé ngập ngừng hoặc nghe truyện cần chỉnh/bỏ `end_prompt`.
7. **R1 không có AEC** khi dùng client kuteo (theo README của client: đọc mic thô, DSP 4 mic của hãng bị bỏ qua; app gốc chưa kiểm tra có dùng DSP hay không). Ảnh hưởng chấm phát âm Azure và việc bé nói chen lúc loa đang phát. **Chưa đo chất lượng mic.**
8. **Không dùng server xiaozhi chính thức (`api.tenclass.net`) cho dự án.** Đã xác minh: sau khi nối WebSocket, server chính thức trả lời vài lượt đầu rồi im lặng trong khi kết nối vẫn mở (xem B7).
9. **Docker trên Windows chưa thử.** Server xinnan 0.9.7 từng chạy trực tiếp trên Windows bằng Python 3.11 venv (`torch==2.2.2` CPU, thêm `opus.dll`), không dùng Docker. Image chính thức đã có `libopus0`/`ffmpeg`. `timezone_offset` trong config phải là **số** (`7`), đặt chuỗi `"+7"` làm server lặp chuỗi. Provider LLM `gemini` của upstream lỗi với `google-generativeai` (đối số `timeout`) → dùng `type: openai` với endpoint tương thích OpenAI. Với spec (dùng OpenAI) mục này chỉ để tham khảo.

## A3. Phần cứng & phân vai

| Thiết bị | Vai trò | Chạy gì |
|---|---|---|
| **Loa Phicomm R1** | Thiết bị của bé A | App xiaozhi (client) — xem ⚠ A2.1 về việc "không sửa" |
| **Board ESP32-S3 + LCD** (XH-S3E-AI_V1.0, amp NS4168, LCD ST7789) | Thiết bị của bé B | Firmware xiaozhi, chỉ đổi `OTA_URL` |
| **PC Windows** | Bộ não | Docker: `xiaozhi-server` (fork) + `tutor/` + trang upload Little Fox |
| **NUC — Home Assistant (HAOS)** | Quản gia | Nhắc giờ học/nghe truyện, nhận báo cáo và đẩy thông báo về điện thoại phụ huynh |

### Loa R1
- Android cũ (RK3229), Wi-Fi 2.4 GHz → đặt gần router.
- Trỏ OTA về `http://<IP_PC>:8003/xiaozhi/ota/`, WebSocket `ws://<IP_PC>:8000/xiaozhi/v1/`.
- **Không sửa client R1.** Mọi logic nằm ở server.
- ⚠ **Đã xác minh khác:** app gốc không nối được kiểu này (A2.1). Muốn R1 làm thiết bị hội thoại phải đổi client hoặc dựng gateway MQTT/UDP. Nếu Minh vẫn giữ nguyên tắc "không sửa client R1" thì R1 chỉ nên dùng làm loa phát.

### Board ESP32-S3 + LCD
- Đổi `OTA_URL` trong menuconfig sang `http://<IP_PC>:8003/xiaozhi/ota/`. Không thêm logic gia sư vào firmware.
- Mic đơn → bé nói gần; đặt mic xa loa để tránh vọng.
- Gắn loa 3W 4Ω có hộp cộng hưởng (loa trần nghe truyện rất mỏng).
- **Màn hình** là lợi thế: server gửi text xuống qua message có sẵn của giao thức xiaozhi (stt/llm text, emotion). Xem mục "Hiển thị màn hình".

### PC Windows
- Docker Desktop tự khởi động cùng Windows; container `restart: unless-stopped`.
- IP LAN tĩnh (đặt DHCP reservation trên router), ưu tiên cắm dây LAN. IP hiện tại của PC trong LAN: `192.168.31.96` (đã dùng khi thử).
- Mở Windows Firewall port 8000 (WS), 8003 (OTA), và port trang upload. Mạng của PC đang ở profile `Public`; đã có sẵn quy tắc Allow cho `Python311\python.exe`, nhưng Docker sẽ cần quy tắc riêng (chưa kiểm tra).
- Chạy local: SileroVAD, SenseVoice ASR, thư viện truyện, SQLite progress. Chỉ LLM (OpenAI) và chấm phát âm (Azure) gọi ra cloud.
- PC không bật thì loa không có gia sư — chấp nhận, không xử lý tự bật máy.

### NUC — Home Assistant
- **Không chạy server gia sư trên NUC** (8 GB RAM đã dùng cho HA, Frigate, Nextcloud, InfluxDB/Grafana; HAOS không chạy Docker tự do).
- Server gửi sự kiện tới HA qua **webhook** (`/api/webhook/<id>`), cấu hình trong `.env`:
  - `tutor_session_ended` — kèm báo cáo tóm tắt → automation HA đẩy `notify.mobile_app_*`.
  - `tutor_server_online` / heartbeat định kỳ → HA có `binary_sensor` biết server đang chạy.
- Automation HA (viết mẫu YAML trong `docs/ha/`):
  - Nhắc giờ học / Story time theo lịch (thông báo điện thoại hoặc phát câu nhắc qua loa khác trong nhà).
  - Cảnh báo nếu tới giờ học mà server gia sư offline.
  - Báo cáo tuần (chủ nhật) chuyển từ webhook sang thông báo.
- Telegram là kênh dự phòng nếu không dùng HA.

## A4. Hồ sơ trẻ & thiết bị

Server phục vụ **hai thiết bị đồng thời**, mỗi thiết bị một phiên độc lập.

### Cấu hình — `data/children.yaml`
```yaml
children:
  - id: be_a
    name: "<tên bé A>"          # gia sư gọi tên bé
    level: 2                    # 1 = mới bắt đầu … 5 = khá
    book: global_success        # thư mục curriculum
    current_unit: 5
    little_fox_level: 2
    daily_minutes: { talk: 15, story: 15 }
  - id: be_b
    name: "<tên bé B>"
    level: 1
    book: global_success
    current_unit: 3
    little_fox_level: 1
    daily_minutes: { talk: 15, story: 15 }

devices:                        # gắn thiết bị ↔ bé; đổi ở đây khi hai bé đổi máy
  "<device_id_R1>":    { child: be_a, type: r1,    has_screen: false }
  "<device_id_ESP32>": { child: be_b, type: esp32, has_screen: true }
```
- `device_id` lấy từ header/handshake mà client gửi lên (MAC hoặc Device-Id) — log ra khi thiết bị kết nối lần đầu để điền. (Xem ⚠ A2.3: với client kuteo là header `device-id` tự sinh; với app gốc là MAC thật qua OTA.)
- Đổi thiết bị giữa hai bé = sửa `devices`, không đụng code. Hỗ trợ reload không cần restart (đọc lại file khi thay đổi).
- Thiết bị chưa có trong `devices` → chế độ khách: free chat cơ bản, không ghi progress, log cảnh báo.

### Cá nhân hoá theo bé
- Prompt hệ thống ghép từ: phần chung + khối theo `level` (độ dài câu, tốc độ nói, mức gợi ý tiếng Việt) + unit hiện tại + 5–10 từ bé hay sai gần đây.
  - Level thấp: câu 3–6 từ, cho phép gợi ý từ tiếng Việt nhiều hơn, khen nhiều hơn.
  - Level cao: câu 8–12 từ, hỏi câu mở ("Why…?", "Tell me about…"), ít gợi ý tiếng Việt.
- TTS: tốc độ đọc theo level (vd. `rate: -15%` cho level 1–2).
- Little Fox: playlist và tiến độ nghe riêng từng bé, lọc theo `little_fox_level`.
- Không bao giờ so sánh hai bé trong lời nói của gia sư ("your brother did better…").

### Chạy đồng thời
- Hai phiên song song phải độc lập hoàn toàn: lịch sử hội thoại, chế độ học, hẹn giờ, playlist.
- SenseVoice dùng chung một instance model; xử lý tuần tự qua hàng đợi nếu cần — đo p95 khi hai bé nói cùng lúc.
- SQLite bật WAL mode để hai phiên ghi song song.

### Hiển thị màn hình (chỉ thiết bị `has_screen: true`)
- Lesson / Review: hiện từ mới + câu mẫu đang học.
- Repeat after me: hiện câu mẫu; sau khi chấm, hiện điểm và đánh dấu từ phát âm sai.
- Story time: hiện tên truyện, series, tập.
- Dùng message text sẵn có của giao thức xiaozhi; nếu cần định dạng riêng thì chỉ thêm tối thiểu, ghi rõ trong `docs/protocol.md`. Kiểm tra firmware hiện tại hiển thị được những gì trước khi thiết kế.
- Thiết bị không có màn hình bỏ qua các message này.

### Học chung (tuỳ chọn, ưu tiên thấp)
- Lệnh "Quiz time for two" trên một thiết bị: đố vui luân phiên, gia sư gọi tên từng bé theo lượt.
- Chỉ dùng câu hỏi ở mức level thấp hơn trong hai bé; không ghi điểm vào progress cá nhân, không xếp hạng thắng–thua.

## A5. Mục tiêu độ trễ (Tier 1, từ lúc bé nói xong)

| Bước | Mục tiêu |
|---|---|
| VAD chờ im lặng | ~0,8 s (không giảm — trẻ hay ngập ngừng) |
| ASR SenseVoice local | ≤ 0,4 s |
| LLM câu đầu tiên (stream) | ≤ 0,7 s |
| TTS câu đầu tiên | ≤ 0,3 s |
| **Tổng tới âm thanh đầu tiên** | **≤ 2 s**, mục tiêu p50 ~1,5 s |

> Tham chiếu đã đo (không phải cấu hình của spec): server xinnan 0.9.7 + Gemini (endpoint OpenAI) + Edge TTS tiếng Việt cho **~10 s** từ lúc gửi câu tới câu nói đầu tiên (lệnh gõ chữ, bỏ qua ASR/VAD). Cần đo lại với cấu hình của spec; mục tiêu ≤ 2 s chưa được chứng minh khả thi.

## A6. Kiến trúc

```
R1 (mic/loa) ──WS──> xiaozhi-server (fork)
                       ├─ VAD: SileroVAD (local)
                       ├─ ASR: SenseVoice (local)          [Tier 1]
                       ├─ LLM: OpenAI gpt-4o-mini (stream)  [Tier 1]
                       ├─ TTS: EdgeTTS (stream theo câu)    [Tier 1]
                       ├─ tutor/  ← code tự viết (xem dưới)
                       │    ├─ curriculum   (unit, từ vựng, mẫu câu)
                       │    ├─ session      (chế độ học, hẹn giờ)
                       │    ├─ progress     (SQLite: lỗi, từ đã học)
                       │    ├─ pronunciation(Azure Pronunciation Assessment) [Tier 2]
                       │    ├─ realtime     (speech-to-speech)                [Tier 3]
                       │    ├─ listening    (thư viện audio Little Fox, lịch nghe, quiz)
                       │    └─ report       (tóm tắt → Telegram / HA)
PC trình duyệt ──HTTP──> tutor/web (trang upload + quản lý thư viện, LAN only)
                       └─ metrics (thời gian từng bước, chi phí)
```

### Nguyên tắc với code upstream
- Hạn chế tối đa sửa core xiaozhi-server. Code mới đặt trong `tutor/` và móc vào qua cơ chế provider/plugin sẵn có của server.
- Khi buộc phải sửa core, đánh dấu `# TUTOR-PATCH:` kèm lý do, để rebase upstream dễ.
- Tên key trong `config.yaml` thay đổi giữa các phiên bản upstream — **luôn đối chiếu file `config.yaml` gốc trong repo** trước khi thêm/đổi key, không đoán. (Phiên bản đã nghiên cứu: tag `v0.9.7`, image `ghcr.io/xinnan-tech/xiaozhi-esp32-server:server_0.9.7`, cấu hình ghi đè ở `data/.config.yaml`.)

## A7. Các giai đoạn

### Tier 1 — Pipeline nhanh, rẻ (làm trước)
- ASR SenseVoice local; ngôn ngữ auto (bé nói lẫn Việt–Anh). ⚠ A2.4.
- LLM `gpt-4o-mini`, streaming, `max_tokens` ~200, `temperature` ~0.6.
- TTS EdgeTTS giọng `en-US-AnaNeural`, đẩy từng câu ra loa ngay khi LLM sinh xong câu đó. ⚠ A2.5.
- `Intent: nointent` (không cần tool HA). `Memory`: tóm tắt ngắn trong phiên.
- VAD `min_silence_duration_ms` ≈ 800 (trẻ ngập ngừng khi nói tiếng Anh — không hạ quá thấp).
- Curriculum + chế độ học + progress + báo cáo phụ huynh.

### Tier 2 — Chấm phát âm
- Chế độ **"Repeat after me"**: loa đọc câu mẫu → bé nhắc lại → gửi audio gốc (không qua ASR) tới Azure Pronunciation Assessment với `reference_text` = câu mẫu.
- Lấy điểm từng từ; từ dưới ngưỡng → khen trước, đọc mẫu chậm lại từ đó, cho bé thử lại tối đa 2 lần.
- Dùng gói miễn phí Azure; đếm số giây đã dùng, dừng tính năng khi gần hết hạn mức tháng.

### Tier 3 — Speech-to-speech cho phiên luyện nói
- Chế độ **"Talk time"** dùng API realtime (OpenAI Realtime bản mini hoặc Gemini Live — chọn cái rẻ hơn tại thời điểm làm, so giá trước).
- Chỉ kích hoạt bằng lệnh giọng nói rõ ràng; **tự tắt sau N phút** (mặc định 15).
- Trần chi tiêu ngày/tháng cứng; vượt trần → quay về Tier 1 và thông báo bằng giọng.
- Có thể tham khảo các server viết bằng Go đã nối giao thức xiaozhi sang Realtime API.

### Nghe hằng ngày — Little Fox (làm song song với Tier 1)
Phát truyện audio Little Fox cho bé nghe mỗi ngày qua loa R1, rồi hỏi lại vài câu về truyện.

- **Nguồn file:** MP3 tải từ tài khoản Little Fox của gia đình, chỉ phát trong nhà. Không tự động tải/scrape từ website Little Fox.
- **Upload:** trang web nhỏ trong `tutor/web` (FastAPI + HTML tĩnh), chỉ bind LAN, không cần đăng nhập nhưng không mở ra Internet.
  - Kéo-thả nhiều file MP3 cùng lúc; tuỳ chọn kèm file `.txt` lời truyện cùng tên.
  - Nhập/sửa metadata: series, số tập, level (Little Fox level 1–9), tiêu đề. Tự đoán từ tên file nếu được.
  - Danh sách thư viện: sắp xếp theo series/tập, đánh dấu đã nghe, xoá, đổi thứ tự.
- **Phát:** tận dụng cơ chế phát nhạc sẵn có của xiaozhi-server (plugin play music / thư mục music) để stream MP3 xuống R1. Kiểm tra code upstream trước, không tự viết lại nếu đã có. (Plugin `play_music` và `hass_play_music` có trong danh sách hàm upstream 0.9.7; chưa chạy thử.)
- **Lệnh giọng nói:** "Story time" (phát tập kế tiếp), "Play it again", "Next story", "Stop", "Louder/Quieter".
- **Danh sách phát hằng ngày:** mặc định phát **tập tiếp theo chưa nghe** trong series đang theo dõi; tuỳ chọn nghe lại tập hôm qua trước (nghe lặp giúp trẻ nhớ). Thời lượng tối đa/ngày cấu hình được (mặc định 15 phút).
- **Hẹn giờ tự phát** (vd. 19:30): server cần đẩy âm thanh khi R1 đang chờ. Client xiaozhi thường chỉ mở WebSocket sau wake word → **phải kiểm tra trước** xem server có chủ động phát được không. Nếu không: phương án dự phòng là Home Assistant nhắc giờ (thông báo/loa khác: "Đến giờ nghe truyện rồi, gọi Miss Lily nhé") và bé tự nói "Story time". (**Đã xác minh một phần:** với client kuteo là kết nối-khi-wake nên server không đẩy được; ⚠ A2.2.)
- **Sau khi nghe:** nếu có lời truyện `.txt`, gia sư hỏi 2–3 câu đơn giản về truyện (ai, cái gì, màu gì…), sinh bằng LLM từ lời truyện, cache lại cho lần sau. Không có lời truyện → chỉ hỏi "Did you like the story? What was your favorite part?".
- **Từ vựng từ truyện:** trích 3–5 từ mới phù hợp lớp 3 từ lời truyện, đưa vào `vocab_seen` để chế độ Review ôn lại.

## A8. Chế độ học

| Chế độ | Kích hoạt (giọng nói) | Mô tả |
|---|---|---|
| Free chat | mặc định | Trò chuyện theo chủ đề lớp 3 |
| Lesson | "Let's learn unit 5" | Dạy từ vựng + mẫu câu của unit, hỏi đáp |
| Repeat after me | "Let's practice speaking" | Tier 2, chấm phát âm |
| Review | "Let's review" | Ôn các từ/câu bé hay sai (từ `progress`) |
| Talk time | "Talk time" | Tier 3, có hẹn giờ |
| Story time | "Story time" / hẹn giờ | Phát truyện Little Fox, sau đó hỏi về truyện |
| Kết thúc | "Goodbye" / hết giờ | Chào, kích hoạt báo cáo |

Nhận diện lệnh bằng so khớp từ khoá đơn giản trên transcript trước khi gọi LLM — không tốn thêm lượt LLM.

## A9. Dữ liệu

### Curriculum — `tutor/curriculum/<book>/unit_XX.yaml`
```yaml
unit: 5
title: "Our hobbies"
vocabulary: [swimming, singing, dancing, drawing, cooking]
patterns:
  - "What's your hobby? — It's {hobby}."
  - "I like {hobby}."
sample_questions:
  - "What's your hobby?"
  - "Do you like singing?"
```
Bộ sách cấu hình trong `config` (`tutor.book`). Nạp vào prompt chỉ phần unit đang học để giữ prompt ngắn.

### Progress — SQLite `data/tutor.db`
Mọi bảng tiến độ có `child_id`; truy vấn luôn lọc theo bé.
- `sessions(id, child_id, device_id, started_at, ended_at, mode, minutes, cost_usd)`
- `mistakes(id, child_id, session_id, type[grammar|vocab|pronunciation], said, correct, word, score, created_at)`
- `vocab_seen(child_id, word, unit, times_seen, times_correct, last_seen)` — khoá chính `(child_id, word)`

- `stories(id, series, episode, level, title, file_path, transcript_path, duration_s, added_at, order_index)`
- `listens(id, child_id, story_id, started_at, seconds_played, completed, quiz_correct, quiz_total)`

Thư viện `stories` dùng chung cho hai bé; tiến độ nghe tính theo `child_id`.

File truyện lưu ở `data/stories/<series>/` (volume Docker, không commit). Không lưu file ghi âm giọng bé quá 24 giờ.

## A10. Prompt gia sư (nguyên tắc)
- Chỉ nói tiếng Anh trình độ A1, câu 5–10 từ, tối đa 2 câu rồi hỏi **một** câu.
- Bé nói tiếng Việt → trả lời tiếng Anh, gợi ý từ tiếng Anh, khuyến khích nói lại.
- Sửa lỗi: khen trước, nhắc lại câu đúng một lần. Không giải thích ngữ pháp.
- Không emoji, không danh sách, không ký hiệu (vì được đọc thành tiếng).
- Nội dung an toàn cho trẻ; không hỏi thông tin cá nhân (địa chỉ, trường, tên đầy đủ).
- Giữ prompt hệ thống ngắn — mỗi token thêm là thêm trễ và tiền ở mọi lượt.

## A11. Báo cáo phụ huynh
- Cuối phiên: một lượt LLM (model rẻ) tóm tắt từ `mistakes` + `vocab_seen` + `listens` của phiên → tiếng Việt, ≤ 8 dòng: thời lượng nói/nghe, truyện đã nghe, kết quả quiz, từ mới, lỗi hay gặp, gợi ý ôn.
- Gửi qua webhook Home Assistant (kênh chính, xem mục NUC) và/hoặc Telegram bot (dự phòng). Cấu hình qua `.env`.
- Có báo cáo tổng tuần (chủ nhật).
- **Báo cáo tách riêng từng bé**, tiêu đề ghi tên bé. Báo cáo tuần gộp một tin nhưng chia hai phần, không so sánh hay xếp hạng hai bé.
- Webhook HA gửi kèm `child_id`, `child_name` để automation phân biệt.

## A12. Hiệu năng & đo đạc
- Log mỗi lượt: `vad_end → asr_done → llm_first_token → tts_first_audio`, đơn vị ms, kèm token in/out và chi phí ước tính.
- Lệnh/script `tutor/tools/latency_report.py` in p50/p95 từng bước từ log.
- Mọi thay đổi ảnh hưởng pipeline phải so p50/p95 trước–sau.

## A13. Chi phí
- File `tutor/pricing.yaml` chứa đơn giá từng API (cập nhật tay; ghi ngày cập nhật).
- Trần chi tiêu `daily_cap_usd`, `monthly_cap_usd` trong config; vượt trần → hạ cấp (Tier 3 → Tier 1, tắt Tier 2) và báo phụ huynh.
- Chi phí ghi theo `child_id`; trần áp cho tổng và có thể đặt riêng từng bé.

## A14. Cấu hình & bí mật
- API key (OpenAI, Azure, Telegram) chỉ để trong `.env`, **không commit**. `.env.example` liệt kê đủ biến.
- Cấu hình người dùng ở `data/.config.yaml` (ghi đè config gốc).
- Không in token/API key ra màn hình hay chat; che trước khi hiển thị.

## A15. Cấu trúc repo (phần tự viết)
```
tutor/
  curriculum/        # YAML theo sách/unit
  modes/             # free_chat, lesson, repeat, review, talk_time
  pronunciation/     # Azure client
  realtime/          # bridge speech-to-speech
  listening/         # thư viện truyện, playlist hằng ngày, quiz
  web/               # FastAPI: upload + quản lý thư viện (LAN only)
  progress.py        # SQLite
  report.py          # tóm tắt + gửi Telegram/HA
  metrics.py
  pricing.yaml
  tools/latency_report.py
tests/tutor/
docs/ha/             # mẫu automation + webhook cho Home Assistant
docker-compose.yml
.env.example
```

## A16. Quy ước code
- Python 3.10+, type hints, async theo phong cách của server upstream.
- `pytest` cho `tutor/`; mock mọi API ngoài, không gọi API thật trong test.
- Log bằng logger của upstream; không log API key hay audio thô.
- Commit nhỏ, mô tả bằng tiếng Việt hoặc tiếng Anh đều được.

## A17. Ngoài phạm vi
- Sửa app/firmware trên R1. (⚠ A2.1: có thể phải xem lại nếu muốn R1 làm thiết bị hội thoại.)
- Điều khiển Home Assistant bằng giọng nói (dự án khác).
- Giao diện web quản lý (manager-api/Java/MySQL của upstream) — không dùng.
- Chạy LLM local.

## A18. Câu hỏi còn mở
- Hai bé học bộ sách nào (Global Success / i-Learn Smart Start / khác)? Tên, level và unit hiện tại của từng bé → điền `children.yaml`.
- Bé nào dùng thiết bị nào lúc đầu.
- Firmware xiaozhi trên ESP32 hiện hiển thị được loại text nào (độ dài, font tiếng Việt, cuộn chữ)?
- ~~Header/handshake nào chứa device ID ổn định cho R1~~ → **Đã trả lời cho R1** (A2.3): khóa theo `device-id`/MAC, không theo UUID. **ESP32 vẫn chưa kiểm tra.**
- Tier 3 chọn OpenAI Realtime mini hay Gemini Live — so giá và độ trễ thực tế từ Đà Nẵng khi tới giai đoạn này.
- Mic của R1 có đủ chất lượng cho chấm phát âm Azure không — cần thử sớm ở Tier 2. (Với client kuteo không có AEC; chưa đo.)
- ~~Server có chủ động đẩy âm thanh xuống R1 khi R1 đang chờ wake word không~~ → **Với client kuteo: không** (kết nối sau wake word) → Story time hẹn giờ chạy qua HA nhắc. Với app gốc (MQTT) chưa biết.
- Chất lượng phát MP3 qua pipeline xiaozhi (thường nén Opus giọng nói) có đủ nghe truyện không — nếu kém, cân nhắc phát qua DLNA/media player của R1 điều khiển từ HA. (Loa báo `dlna_open: true`; chưa thử.)
- **Mới:** Minh chọn hướng nào cho R1 (A2.1: thay client / gateway MQTT-UDP / R1 chỉ phát)?
- **Mới:** ASR cho tiếng Việt (A2.4) và TTS dự phòng (A2.5) dùng gì?

---

# PHẦN B — BỐI CẢNH KỸ THUẬT LOA R1

## B1. Thiết bị

| | |
|---|---|
| Loa | Phicomm R1, tên thiết bị `Phicomm_R1_7C0B` |
| IP trong LAN | `192.168.31.143`; MAC `fc:7c:02:57:7c:0b` |
| SoC | Rockchip RK3229 (`ro.board.platform=rk322x`), ABI `armeabi-v7a`; RAM 501 MB (`MemFree` ~20 MB lúc đo) |
| Android | 5.1.1 (API 22), build `LMY49F release-keys` |
| Model prop | `rk322x-box` |
| Firmware gốc (`ro.build.version.incremental`) | **3415** |
| Phần mềm trợ lý | **AI-Box / AI Box Plus**, gói `info.dourok.voicebot` (`versionName` 4.0; lệnh `get_version` báo App version **5.2.0**; `get_info` báo `ver: 1877`, `u_ver: 1000`). Đây là phiên bản app, không phải firmware gốc |
| Gói hệ thống của hãng | `com.phicomm.speaker.player` 0.2.5 (EchoService, DLNA/AirPlay/NetPlayer), `com.phicomm.speaker.launcher`, `com.phicomm.speaker.netctl`, `com.phicomm.speaker.device` |
| Múi giờ | **`Asia/Ho_Chi_Minh`** (đã đổi ngày 2026-10-24 theo yêu cầu của Minh; ban đầu là `Asia/Shanghai`, lệch +1 giờ) |
| Mạng | SSID `Qwerty`, 2.4 GHz kênh 1, RSSI thường −43…−54 (có lúc −66), 65–72 Mbps; ping router 4–15 ms, ping `api.tenclass.net` ~50 ms, mất gói 0%. DNS: router `192.168.31.1` |
| Khởi động lại | Loa khởi động lại **nhiều lần** trong ngày 2026-10-24: suy từ `uptime`, khoảng 09:55, 10:37, 11:20, ~15:58 và ~18:00 giờ VN. **Chưa rõ nguyên nhân.** Hai lần (10:37, 11:20) xảy ra ngay sau khi mình đổi múi giờ (10:31) và đổi OTA (~11:1x) nên không loại trừ do tác động đó; lần ~18:00 không có thao tác nào của mình |

**Lưu ý sửa sai:** chip R1 là **RK3229**, KHÔNG phải Amlogic S905D (S905D là của hộp Phicomm N1). Các bản Armbian/OpenWrt cho N1 không dùng được cho R1.

HA server của Minh ở `192.168.31.72:8123`, chạy HTTPS với chứng chỉ chỉ hợp lệ cho `holoto.duckdns.org` (hết hạn 2026-12-10). Gọi bằng IP sẽ lệch tên chứng chỉ. Cấu hình HA trên loa đọc ngày 2026-10-24 đã dùng **`https://holoto.duckdns.org`** (không còn là IP như ghi chú cũ).

## B2. Các cổng trên loa (đã xác minh)

| Cổng | Dịch vụ | Ghi chú |
|---|---|---|
| 5555 | **ADB mạng** | **Đã xác minh mở.** Không cần xác thực. Chạy với `uid=2000(shell)` |
| 8080 | WebSocket điều khiển loa (`SpeakerConnection`) | JSON `{"type": ...}`. Do dịch vụ hệ thống của hãng phục vụ (nhiều khả năng lớp `com.xiaofei.server`, chưa xác minh), **vẫn chạy khi app AI-Box bị ẩn** (đã xác minh) |
| 8081 | HTTP, trang web điều khiển "AI BOX" (Tailwind, Live2D) | Do app AI-Box phục vụ; biến mất nếu ẩn app. Phục vụ `js/*.js` không cần đăng nhập |
| 8082 | WebSocket AI-Box Plus (`AiboxPlusConnection`) | JSON `{"action": ...}`; do app AI-Box phục vụ |
| 8088 | Control panel của client `kuteo-git/xiaozhi-android` | Chỉ khi cài client đó; đã dùng thử (B9) |

Không có xác thực ở bất kỳ cổng nào trong số trên.

## B3. Giao thức WebSocket cổng 8080 (type-based)

Gửi `{"type": "get_info"}` → phản hồi `{"msg":"ok","type":"get_info","code":200,"data":"<chuỗi JSON>"}` (`data` là JSON lồng nhau dạng chuỗi, phải `json.loads` lần nữa).

Trường chính trong `get_info.data`: `vol` (0–15), `play_state` (bool), `mute` (bool), `device_name`, `device_udid`, `ver`, `dlna_open` (true), `play_mode`, `PlayerType`, `ttsModelType` (`SWEET`), `music_light_*`, `airplay_open`.

Lệnh đã **đọc từ mã giao diện** (đã thử thực tế chỉ `get_info`, `get_eq_config` và `shell`):

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
| Shell | `{"type":"shell","type_id":"myshell","shell":"<lệnh>"}` → phản hồi `type: "shell"` (`data` gồm lệnh, `exitCode`, rồi đầu ra) |

**Kênh `shell` chạy với `uid=1000(system)`** (đã xác minh), mạnh hơn ADB (`uid=2000`). Đã dùng nó cho: `getprop`, `pm install/hide/unhide/disable/uninstall`, `am start/force-stop`, `monkey`, `service call alarm 3 s16 <múi giờ>` (đổi múi giờ; ADB bị từ chối quyền này). Loa **không có** `head`, `tail`, `which`, `nc`, `pidof`; có `grep`, `ping`, `dumpsys`, `logcat`.

Ghi chú vận hành đã học:
- `adb shell pm ...` thường báo `error: closed` (kể cả `pm list packages`, `pm install`); dùng kênh shell 8080 thay thế. `adb install` kiểu mới cũng treo; cách chạy được: `adb push <apk> /data/local/tmp/` rồi `pm install -r` qua kênh 8080.
- Trong Git Bash cần `MSYS_NO_PATHCONV=1` để đường dẫn `/data/...` không bị đổi.
- **Log của loa bị nhiễu nặng:** driver mic `UNI_4MIC` xả khoảng 4.500 dòng/giây nên bộ đệm logcat quay vòng trong vài giây. Đọc log quá khứ gần như vô ích; phải **bắt log trực tiếp** với bộ lọc tag, ví dụ `logcat -v threadtime -s ChatActivity:V ActivationActivity:V PahoMqttProtocol:V UdpAudioChannel:V`.
- Lớp `com.xiaofei.server$WsdServer.onMessage` (có thể là chính máy chủ cổng 8080, chưa xác minh) ném `NullPointerException` (`getSharedPreferences` trên context null) hàng chục lần khi app chạy; tác động chưa rõ.

Chưa tìm ra lệnh tắt tiếng (loa có báo `mute` nhưng không thấy lệnh đặt).

## B4. Giao thức WebSocket cổng 8082 (action-based)

Các `action` thấy trong mã: `chat_get_state`, `chat_get_history`, `chat_send_text` (`{"text": ...}`), `chat_wake_up`, `chat_test_mic`, `ota_get`, `ota_set` (`{"ota_url": ...}`), `hass_get`, `hass_set`, `hass_pipelines_get`, `pause`/`resume`/`stop`/`next`/`previous`/`seek`, `alarm_*`, `playlist_*`, `search_songs`/`search_zing`/`play_zing`, `wifi_*`, `wake_word_*`, `get_version`, `get_premium`, nhiều thứ khác.

Đã xác minh dùng được: `ota_get`, `ota_set`, `chat_get_history` (trả các `chat_message` có `content` và `timestamp` giây Unix — rất hữu ích để chẩn đoán).

Cấu hình đọc được (**token Home Assistant luôn bị che, không được in ra**):
- `hass_config`: URL `https://holoto.duckdns.org`, `agent_id` = `conversation.google_ai_conversation`, `pipeline_name` = "-- Mặc định --", `configured: true`.
- `ota_config`: hiện `https://api.tenclass.net/xiaozhi/ota/` (đã khôi phục); các lựa chọn: `https://api.tenclass.net/xiaozhi/ota/`, `https://me.ai-box.vn/xiaozhi/ota/`, `home_assistant`.
- Wake word: bật, độ nhạy 0.90, cửa sổ 5 (giới hạn 5–7).

**Chú ý:** cài đặt OTA **dùng chung** giữa app AI-Box gốc và client kuteo (khi bật lại app gốc nó đọc đúng địa chỉ OTA mà client kia đã đặt). App chỉ đọc OTA lúc khởi động hoặc lúc bắt đầu phiên; đổi OTA xong cần khởi động lại app để có hiệu lực.

## B5. Wake word

Với app gốc: cố định là **"Ô Kê Na Bu"** (OK Nabu). Chỉ cho bật/tắt, chỉnh độ nhạy và cửa sổ nhận diện. **Không có lệnh đổi từ khóa.** Có nút "Wake Up" (`chat_wake_up`) để kích hoạt bằng tay.

Client `kuteo-git/xiaozhi-android` (đã thử): chọn qua `GET /api/setup/wake?engine=alexa|nabu|mai_oi` rồi khởi động lại app; mặc định `alexa`, đã đặt `nabu`. Khác: shj4588 đổi sang "小智小智" (chưa thử).

## B6. Tích hợp Home Assistant đã viết

Thư mục `custom_components/phicomm_r1/` (trong repo HomeAssistant, **chưa commit, chưa cài lên HA**):
- Config flow (IP + cổng 8080), một thực thể `media_player` (phát/tạm dừng/bài kế/bài trước/âm lượng, trạng thái, âm lượng 0–15 quy về 0–1, tắt tiếng chỉ đọc).
- Cập nhật mỗi 5 giây qua kết nối WebSocket ngắn; client trong `api.py`.
- Đã kiểm tra: biên dịch được và `get_info` đọc đúng loa thật. **Chưa thử:** các lệnh điều khiển, chạy trong HA thật. Vì cổng 8080 độc lập với app AI-Box, tích hợp này vẫn dùng được khi app chat bị ẩn/thay.
- Phát nhạc/TTS: dùng tích hợp **DLNA Digital Media Renderer** có sẵn của HA (loa báo `dlna_open: true`); chưa thử.

Add-on server Xiaozhi trong repo HA (`D:\Projects\HomeAssistant\xiaozhi\`, upstream `v0.9.7`) **chưa chạy thực tế** (không Docker, chưa cài lên HAOS). Ngày 2026-10-24 mình đã chạy **server upstream cùng phiên bản** trực tiếp trên Windows với cấu hình tự viết (B9), không dùng `run.sh` của add-on.

## B7. Sự cố: chat AI "lúc được lúc không"

Triệu chứng (Minh xác nhận): cả lệnh nhà thông minh lẫn chat thường đều có lúc không phản hồi; tin của Minh vẫn hiện trong khung chat nhưng không có trả lời. ESP32 của Minh dùng cùng máy chủ vẫn phản hồi tốt.

**Đã loại trừ (đã đo):** Wi-Fi yếu/mất gói (RSSI tốt, 0% mất gói), thiếu RAM hay app bị giết (không có sự kiện `am_kill`/`crash`), nghẽn UDP phía loa (`RcvbufErrors = 0`, `InErrors = 0`), rớt kết nối mạng (app giữ kết nối nhiều phút không báo lỗi).

**Bằng chứng về vị trí lỗi:**
- Giao thức thật của app AI-Box là **MQTT (báo hiệu) + UDP (âm thanh)**, không phải WebSocket như ghi chú cũ. OTA chính thức trả cả `mqtt` lẫn `websocket`.
- Lịch sử chat của loa (`chat_get_history`) cho thấy chữ của Minh **đã được nhận dạng và lên server** (hiện `🎤 …`), nhưng câu trả lời không về; khoảng 62–65 s sau loa chỉ nói "tạm biệt" (phiên hết hạn). Trong log, loa vào trạng thái `Speaking...` mà không có `Playback loop started` (không có dữ liệu âm thanh đến để phát).
- Với client kuteo nối **WebSocket tới server chính thức** (`wss://api.tenclass.net/xiaozhi/v1/`): trả lời vài lượt đầu rồi **im lặng, kết nối vẫn mở, app không báo lỗi**. Khởi động lại app thì lại trả lời 2 lượt đầu rồi im. Không phụ thuộc độ dài hay nội dung câu (cả "một cộng hai bằng mấy" cũng không được trả lời). → Lỗi **không nằm ở đường UDP**, mà ở phía server chính thức/phiên.
- Với **server xinnan tự host trong LAN** + cùng client: server nhận và xử lý nhiều câu liên tiếp (không im lặng); lỗi duy nhất thấy được là Edge TTS đôi khi không tạo được giọng (A2.5).

**Kết luận hiện tại (giả thuyết mạnh, chưa chứng minh được phía server của họ):** nguyên nhân gốc nằm ở **server xiaozhi chính thức** (hoặc cách nó xử lý phiên), không phải phần cứng/Wi-Fi của R1. Ngoài ra: câu hỏi về mô hình LLM chọn trên console xiaozhi.me (trong menu có `GPT-5 (Thử nghiệm nội bộ)`) có thể liên quan độ trễ; **chưa thử đổi**.

**Giả thuyết riêng về "ngoại tuyến sau khi khởi động":** DNS của loa lỗi vài giây đầu sau khi khởi động (`EAI_NODATA`), nếu app gọi OTA đúng lúc đó có thể nằm ở trạng thái ngoại tuyến đến khi khởi động lại app. Chưa bắt được log lúc khởi động để xác nhận. Kèm theo: kết nối lại phiên chat chậm, **9–14 giây** mỗi lần.

**Lệnh nhà thông minh:** cấu hình HA trên loa đã dùng tên miền (`holoto.duckdns.org`); agent `conversation.google_ai_conversation` vẫn chưa kiểm tra có tồn tại không. Router không NAT loopback port 8123 nên dùng tên miền trong LAN có thể không được.

## B8. Phương án firmware / client

**Không có ảnh firmware thay thế Android cho R1.** Tìm kiếm web ngày 2026-10-24 không thấy dự án Armbian/OpenWrt/ROM nào riêng cho Phicomm R1; chỉ có bản cộng đồng cho hộp RK322x nói chung (thường phải vá nhân và device tree riêng, ví dụ ReSpeaker Core v2 cũng RK3229). Port sang Linux là việc tự làm, rủi ro brick, và mất DSP mic của hãng; **không khuyến nghị** vì lỗi nằm ở tầng ứng dụng/server. Mã nguồn AI-Box Plus không tìm thấy (có vẻ đóng).

| Dự án | Loại | Điểm đáng chú ý |
|---|---|---|
| `kuteo-git/xiaozhi-android` | APK client mỏng | **Đã thử (B9).** Chỉ kết nối khi wake word; panel cổng 8088; hỗ trợ cả `WebsocketProtocol` lẫn `MqttProtocol`; không có AEC; chưa thấy giấy phép; cần server tương thích (đã chạy được với server xinnan 0.9.7 stock cho hội thoại cơ bản) |
| `kuteo-git/robot-esp32` | Server đi kèm client trên | Chưa thử |
| `hoanglt1223/db-robot-phincomR1` (nhánh của `ledienbien-ai`) | APK đầy đủ, UI tiếng Việt | Chưa thử. Chọn wake word; keystore công khai; trình cài kiểu `curl \| bash`; mặc định `sv1.dbrobot.vn` |
| `shj4588/Phicomm_R1_XiaoZhi_Client` | 3 APK vá vào tiến trình giọng nói gốc | Chưa thử. Giữ xử lý 4 micro (AEC, beamforming); **bắt buộc firmware gốc đúng 3448** (loa này **3415**); console cổng 8080 không xác thực; không giấy phép; wake word "小智小智" |
| `xuan2261/r1-xiaozhi` | APK đơn giản, MIT | Chưa thử. Wake word chỉ phát hiện theo năng lượng |
| `cyberty/R1up4Mac` | Script nâng cấp firmware gốc qua ADB | Chưa thử. Có bước `3415 → 3448`; cảnh báo không cắt nguồn |

## B9. Nhật ký thử nghiệm 2026-10-24 (để khỏi làm lại)

**Server xinnan tự host trên PC (Windows, không Docker):** clone tag `v0.9.7`; Python **3.11** venv (3.13 không có `torch==2.2.2`); `pip install -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu`; thiếu `opus.dll` → lấy `libopus-0.x64.dll` từ wheel `discord.py` đổi tên `opus.dll` đặt trong `venv\Scripts` (kiểm tra mã hóa/giải mã Opus thành công); mô hình Vosk tiếng Việt `vosk-model-small-vn-0.4` (~33 MB) từ `alphacephei.com`; nâng `edge-tts` lên 7.3.1; LLM Gemini qua `https://generativelanguage.googleapis.com/v1beta/openai/` (model `gemini-flash-lite-latest` ổn; `gemini-2.5-flash`/`3.5-flash` bị 503, `gemini-flash-latest` treo). Cấu hình ghi ở `data/.config.yaml`. OTA tự host trả **chỉ WebSocket** (`ws://<IP_PC>:8000/xiaozhi/v1/`). Kiểm thử bằng client giả: nhận 138 khung Opus cho một câu trả lời. Độ trễ ~10 s tới câu đầu.

**Client kuteo trên R1:** build `./gradlew assembleRelease` trong **4 phút 18 giây** với JDK 21 của Android Studio, SDK 35, CMake 3.22.1 (NDK 28 có sẵn vẫn qua). `applicationId` = `info.dourok.voicebot.dev` (cài song song, không ghi đè app gốc); ký bằng khóa debug. Cài qua `adb push` + `pm install -r` bằng kênh shell 8080; phải **ẩn app gốc** (`pm hide info.dourok.voicebot`) để nhường micro. Cấu hình qua panel `http://192.168.31.143:8088`: `GET /api/setup/server?ota=<URL>` (suy WebSocket từ OTA; nếu OTA lỗi nó **tự đoán** `ws://<host>:8000/...`), `/api/setup/wake?engine=nabu`, `/api/say?text=` (gõ chữ; **phải gửi UTF-8**, `curl` trên Windows làm hỏng dấu), `/api/restart`, `/api/logs`, `/api/state`. Cài đặt chỉ có hiệu lực **sau khi khởi động lại app**. Chạy với server xinnan: hội thoại bằng chữ ổn định qua nhiều phiên.

**Thử server chính thức với client kuteo:** `POST https://api.tenclass.net/xiaozhi/ota/` cần `Device-Id` **đúng định dạng MAC** (nếu không trả `HTTP 400 Invalid MAC address`; panel gửi Android ID nên bị 400, đó là lý do "OTA không trả lời"). Với MAC hợp lệ server trả `mqtt` + `websocket` (`wss://api.tenclass.net/xiaozhi/v1/` + token), không đòi mã kích hoạt cho định danh của app gốc. Với định danh của client kuteo, server chat trả "Please log in to the console to add this device and enter the verification code …" (mã 6 số do **server cấp**, không có sẵn trên loa; mỗi lần gọi OTA có thể đổi). Nối `wss://` từ R1 **thành công** (TLS/mạng ổn), nhưng server im sau vài lượt (B7).

**Trạng thái cuối (2026-10-24, sau khi dọn):**
- App AI-Box gốc `info.dourok.voicebot` đã hiện lại và chạy; client kuteo **đã gỡ** (`pm uninstall`); không còn gói bị ẩn/vô hiệu hóa.
- OTA của app gốc đặt lại `https://api.tenclass.net/xiaozhi/ota/`.
- Múi giờ loa `Asia/Ho_Chi_Minh` (giữ lại); ADB 5555 vẫn mở như ban đầu.
- Server tự host trên PC, môi trường Python, mã nguồn client, log đã **xóa khỏi PC**.
- Thư mục sao lưu APK (`backup-apk/`) từng có trong repo **không còn** (không rõ ai xóa); APK gốc vẫn nằm trên loa: `/data/app/info.dourok.voicebot-1/base.apk`, `/data/app/com.phicomm.speaker.player-1/base.apk`, `/system/app/{EchoService,Launcher,NetControl}/*.apk`; lấy lại bằng `adb pull`.

**Hoàn tác nhanh nếu lặp lại thử nghiệm:** `pm unhide info.dourok.voicebot` và đặt lại OTA (`ota_set` qua 8082) về `https://api.tenclass.net/xiaozhi/ota/`, rồi khởi động lại app AI-Box (`am force-stop` + `monkey -p info.dourok.voicebot -c android.intent.category.LAUNCHER 1`).

**Về dịch vụ AI-Box Plus / `me.ai-box.vn`:** chưa xác định miễn phí hay có phí (trang chỉ tải bằng JavaScript). Trong APK có `get_premium`, liên kết thanh toán `apipay.vn`, `BankNotifyManager` nên có phần trả phí; chưa rõ OTA `me.ai-box.vn` thuộc loại nào. Trang `ai-box.vn/mcp-hub` đòi một địa chỉ MCP riêng của agent (kèm token), không phải `wss://api.tenclass.net/xiaozhi/v1/`; **không nhập token vào dịch vụ bên thứ ba nếu chưa tin họ.**

## B10. Rủi ro và quy tắc

- Đa số dự án client không có giấy phép rõ ràng hoặc ghi "chỉ nghiên cứu".
- Nhiều trình cài chạy script tải từ mạng (`curl | bash`, `wget | sh` từ tên miền lạ). Phải đọc script trước khi chạy.
- Panel/console trên loa (5555/8080/8081/8082/8088) **không có xác thực**; ai trong LAN cũng điều khiển/cài app được.
- Cài client mới phải ẩn gói gốc (`pm hide`, đảo ngược bằng `pm unhide`); ghi lại gói đã ẩn.
- Đổi OTA hoặc cài/ẩn app có thể làm loa khởi động lại; nếu sai địa chỉ OTA thì chat chết cho tới khi hoàn tác.
- Không cắt nguồn khi nâng cấp firmware.
- Giữ nguyên AI-Box để dự phòng trước khi thử client khác.
- **Quyền:** các lệnh ghi lên loa (đổi OTA, cài/ẩn/gỡ app, đổi múi giờ) chỉ làm khi Minh đồng ý rõ ràng cho từng việc; ngày 2026-10-24 Minh đã cho phép và đã thực hiện các việc liệt kê ở B9. Lệnh tải mã từ mạng (pip, tải DLL/mô hình, build) cũng cần Minh đồng ý.
- Không in token HA hay API key ra màn hình; che trước khi hiển thị. Key Gemini dùng khi thử đã nằm trong file `.env` (đã xóa); **nên thu hồi key đó** ở Google AI Studio nếu không dùng nữa.

## B11. Việc còn dang dở / gợi ý tiếp theo

1. **Quyết định hướng cho R1** (A2.1): thay client / gateway MQTT-UDP / chỉ làm loa phát. Đây là điều kiện để dự án gia sư dùng R1 làm thiết bị hội thoại.
2. Dựng thử `xiaozhi-server` + `tutor/` bằng **Docker** trên PC (chưa thử); kiểm tra ASR cho tiếng Việt (SenseVoice không hỗ trợ), TTS dự phòng (Edge TTS chập chờn), và đo độ trễ thật so với mục tiêu ≤ 2 s.
3. Kiểm tra ESP32 gửi `device-id` nào và hiển thị được gì trên LCD.
4. Làm rõ vì sao loa **tự khởi động lại** (xem tính năng `AutoRebootManager` của app, nguồn điện, hay tác động của lệnh đã chạy) và lỗi DNS ngay sau khi khởi động; theo dõi lại sự cố "ngoại tuyến".
5. Thử đổi mô hình LLM trên console xiaozhi.me (ví dụ `Qwen 3.6 (Nhanh)`, `Xiaozhi Lite`) nếu vẫn dùng app gốc với server chính thức, để xem có hết im lặng không.
6. Cài `custom_components/phicomm_r1/` lên HA và thử các lệnh điều khiển (hỏi Minh trước khi gửi lệnh gây ra tiếng); thêm dịch vụ "wake up" (`chat_wake_up`).
7. Sửa/kiểm tra agent HA `conversation.google_ai_conversation` trên loa nếu muốn lệnh nhà thông minh ổn định.
8. Thử phát truyện qua **DLNA** từ HA (loa báo `dlna_open: true`) làm phương án cho Story time hẹn giờ.
9. Nếu cần chất lượng thu âm tốt hơn: cân nhắc shj4588 sau khi nâng firmware lên 3448 bằng R1up4Mac (rủi ro, cần cẩn trọng).
10. Sao lưu lại APK gốc từ loa vào nơi an toàn ngoài repo.
