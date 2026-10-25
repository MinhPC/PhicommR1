# Lớp mỏng trên image upstream: nâng edge-tts vì bản ghim 7.2.6 bị Microsoft trả HTTP 403
# (đã gặp ngày 2026-10-24; 7.3.1 chạy được).
FROM ghcr.io/xinnan-tech/xiaozhi-esp32-server:server_0.9.7
RUN pip install --no-cache-dir -U "edge-tts>=7.3.1"
