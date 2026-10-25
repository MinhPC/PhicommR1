"""Sinh data/.config.yaml cho xiaozhi-server từ .env. Chạy: python tutor/tools/gen_config.py [IP_PC]

Không in key. Tên khoá đã đối chiếu với upstream v0.9.7 (config.yaml).
IP_PC mặc định tự dò (IP LAN của máy); đặt SERVER_HOST trong .env để cố định.
"""
from __future__ import annotations

import socket
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tutor.prompt import COMMON, LEVEL_BLOCKS  # noqa: E402


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.split("#")[0].strip().strip("\"'")
    return env


def lan_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # không gửi gói nào, chỉ chọn giao diện mạng
        return s.getsockname()[0]
    finally:
        s.close()


def build_config(env: dict, host: str) -> dict:
    return {
        "server": {
            "ip": "0.0.0.0", "port": 8000, "http_port": 8003,
            "websocket": f"ws://{host}:8000/xiaozhi/v1/",
            "vision_explain": f"http://{host}:8003/mcp/vision/explain",
            "timezone_offset": 7,           # phải là SỐ; chuỗi "+7" làm server lặp chuỗi
            "mqtt_gateway": None, "udp_gateway": None,
        },
        "log": {"log_level": "INFO", "log_dir": "tmp"},
        "prompt_template": "prompt-template.txt",
        "prompt": COMMON + " " + LEVEL_BLOCKS[2],   # tạm thời; sau này ghép theo bé
        "enable_greeting": False,
        "selected_module": {
            "VAD": "SileroVAD", "ASR": "FunASR", "LLM": "OpenAILLM",
            "TTS": "EdgeTTS", "Memory": "nomem", "Intent": "nointent",
        },
        "VAD": {"SileroVAD": {"min_silence_duration_ms": 800}},  # trẻ ngập ngừng; không hạ thấp hơn
        "ASR": {"FunASR": {"language": "auto"}},
        "LLM": {"OpenAILLM": {
            "type": "openai", "model_name": "gpt-4o-mini",
            "base_url": "https://api.openai.com/v1", "api_key": env["OPENAI_API_KEY"],
            "temperature": 0.6, "max_tokens": 200,
        }},
        "TTS": {"EdgeTTS": {
            "type": "edge_stream", "voice": "en-US-AnaNeural", "language": "English", "output_dir": "tmp/",
        }},
    }


def main() -> int:
    env_path = ROOT / ".env"
    if not env_path.exists():
        print(f"Không thấy {env_path}")
        return 1
    env = load_env(env_path)
    if not env.get("OPENAI_API_KEY"):
        print("Thiếu OPENAI_API_KEY trong .env")
        return 1
    host = sys.argv[1] if len(sys.argv) > 1 else env.get("SERVER_HOST") or lan_ip()
    cfg = build_config(env, host)
    out = ROOT / "data" / ".config.yaml"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml.safe_dump(cfg, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"Đã ghi {out}")
    print(f"  WebSocket : ws://{host}:8000/xiaozhi/v1/")
    print(f"  OTA       : http://{host}:8003/xiaozhi/ota/")
    print(f"  LLM       : gpt-4o-mini, key={env['OPENAI_API_KEY'][:3]}***")
    return 0


if __name__ == "__main__":
    sys.exit(main())
