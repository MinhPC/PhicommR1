"""Kiểm tra OPENAI_API_KEY trong .env bằng một lệnh gọi nhỏ. Chạy: python tutor/tools/check_openai.py

Chỉ in kết quả và độ trễ; KHÔNG bao giờ in key. Chỉ dùng thư viện chuẩn.
"""
from __future__ import annotations

import http.client
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(__file__).resolve().parents[2] / ".env"
MODEL = "gpt-4o-mini"


def load_env(path: Path) -> dict:
    env = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.split("#")[0].strip().strip("\"'")
    return env


def stream_ttft(key: str, runs: int = 6) -> list[float]:
    """Đo thời gian tới token nội dung đầu tiên (streaming), tái dùng một kết nối như server thật.

    Lượt đầu là khởi động (TLS + DNS) và được bỏ khỏi thống kê.
    """
    conn = http.client.HTTPSConnection("api.openai.com", timeout=40)
    body = json.dumps({"model": MODEL, "max_tokens": 40, "stream": True,
                       "messages": [{"role": "system", "content": "You are a friendly English tutor for a child. Use at most 2 short sentences, then ask one question."},
                                    {"role": "user", "content": "I like swimming."}]})
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    times = []
    for _ in range(runs):
        t0 = time.time()
        conn.request("POST", "/v1/chat/completions", body, headers)
        resp = conn.getresponse()
        if resp.status != 200:
            print(f"  LỖI HTTP {resp.status}: {resp.read().decode(errors='replace').replace(key, '***')[:200]}")
            return times
        first = None
        for raw in resp:  # đọc hết để kết nối dùng lại được
            line = raw.decode(errors="replace").strip()
            if first is None and line.startswith("data:") and '"content":"' in line:
                first = time.time() - t0
        times.append(first if first is not None else time.time() - t0)
    return times[1:]


def main() -> int:
    if not ENV.exists():
        print(f"Không thấy {ENV}")
        return 1
    key = load_env(ENV).get("OPENAI_API_KEY", "")
    if not key:
        print("OPENAI_API_KEY trống hoặc thiếu trong .env")
        return 1
    print(f"Đọc được key: {key[:3]}*** ({len(key)} ký tự)")
    body = {"model": MODEL, "max_tokens": 30, "stream": False,
            "messages": [{"role": "system", "content": "You are a friendly English tutor for a child. Reply in one short sentence."},
                         {"role": "user", "content": "Hello!"}]}
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    t0 = time.time()
    try:
        out = json.load(urllib.request.urlopen(req, timeout=40))
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace").replace(key, "***")[:300]
        print(f"LỖI HTTP {e.code}: {msg}")
        return 2
    except Exception as e:
        print(f"LỖI mạng: {e}")
        return 2
    dt = time.time() - t0
    print(f"OK ({MODEL}, {dt:.1f}s): {out['choices'][0]['message']['content']}")
    print(f"Token: {out.get('usage')}")
    ts = stream_ttft(key)
    if ts:
        ordered = sorted(ts)
        print(f"Streaming, tới token đầu (kết nối tái dùng, {len(ts)} lượt): "
              f"min {ordered[0]:.2f}s, trung vị {statistics.median(ts):.2f}s, max {ordered[-1]:.2f}s")
        print("Lưu ý: đây là tới TOKEN đầu tiên. Mục tiêu spec (≤ 0,7 s) là tới CÂU đầu hoàn chỉnh, nên con số thật cao hơn một chút.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
