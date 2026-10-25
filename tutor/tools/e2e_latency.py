"""Đo độ trễ đầu-cuối bằng client giả. Chạy TRONG container:
    docker exec xiaozhi-server python /opt/xiaozhi-esp32-server/tutor/tools/e2e_latency.py "I like swimming" 4

Quy trình: edge-tts tạo giọng nói → ffmpeg đổi 16 kHz mono → mã hoá Opus 60 ms → gửi theo thời gian thực
qua WebSocket (listen mode auto) → sau đó gửi im lặng để VAD tự chốt → đo từ lúc NÓI XONG tới:
  stt (server báo đã nhận dạng), tts start, và khung âm thanh đầu tiên trả về.
"""
from __future__ import annotations

import asyncio
import json
import statistics
import subprocess
import sys
import time

import edge_tts
import opuslib_next
import websockets

URL = "ws://127.0.0.1:8000/xiaozhi/v1/"
RATE, FRAME_MS = 16000, 60
FRAME_SAMPLES = RATE * FRAME_MS // 1000
SILENCE_S = 3.0  # đủ để VAD (800 ms) chốt hết câu


async def synth(text: str, voice: str = "en-US-GuyNeural") -> bytes:
    mp3 = b""
    async for ch in edge_tts.Communicate(text, voice).stream():
        if ch["type"] == "audio":
            mp3 += ch["data"]
    if not mp3:
        raise RuntimeError("edge-tts không trả âm thanh")
    pcm = subprocess.run(["ffmpeg", "-loglevel", "error", "-i", "pipe:0", "-f", "s16le", "-ar", str(RATE), "-ac", "1", "pipe:1"],
                         input=mp3, capture_output=True, check=True).stdout
    return pcm


def opus_frames(pcm: bytes) -> list[bytes]:
    enc = opuslib_next.Encoder(RATE, 1, opuslib_next.APPLICATION_AUDIO)
    step = FRAME_SAMPLES * 2
    pcm += b"\x00" * (-len(pcm) % step)
    return [enc.encode(pcm[i:i + step], FRAME_SAMPLES) for i in range(0, len(pcm), step)]


async def one_turn(speech: list[bytes], silence: list[bytes]) -> dict:
    async with websockets.connect(URL, additional_headers={"Device-Id": "aa:bb:cc:dd:ee:02", "Client-Id": "e2e-test"},
                                  max_size=None) as ws:
        await ws.send(json.dumps({"type": "hello", "version": 1, "transport": "websocket",
                                  "audio_params": {"format": "opus", "sample_rate": RATE, "channels": 1, "frame_duration": FRAME_MS}}))
        await asyncio.wait_for(ws.recv(), 10)
        await ws.send(json.dumps({"type": "listen", "state": "start", "mode": "auto"}))

        marks: dict = {"stt_text": None}
        t_end = {"v": None}

        async def reader():
            async for m in ws:
                now = time.time()
                if isinstance(m, bytes):
                    marks.setdefault("first_audio", now)
                    marks.setdefault("frames", []).append(m)
                    continue
                j = json.loads(m)
                if j.get("type") == "stt":
                    marks.setdefault("stt", now)
                    marks["stt_text"] = j.get("text")
                elif j.get("type") == "tts" and j.get("state") == "start":
                    marks.setdefault("tts_start", now)
                elif j.get("type") == "tts" and j.get("state") == "stop" and "first_audio" in marks:
                    return

        task = asyncio.create_task(reader())
        for f in speech:                     # thời gian thực: mỗi khung cách nhau 60 ms
            await ws.send(f)
            await asyncio.sleep(FRAME_MS / 1000)
        t_end["v"] = time.time()
        for f in silence:
            await ws.send(f)
            await asyncio.sleep(FRAME_MS / 1000)
            if "first_audio" in marks:
                break
        try:
            await asyncio.wait_for(task, 20)
        except asyncio.TimeoutError:
            task.cancel()
        t0 = t_end["v"]
        d = lambda k: (marks[k] - t0) if k in marks else None  # noqa: E731
        return {"stt": d("stt"), "tts_start": d("tts_start"), "first_audio": d("first_audio"), "text": marks["stt_text"],
                "frames": marks.get("frames", [])}


def audio_stats(frames: list[bytes]) -> str:
    """Giải mã Opus nhận được: thời lượng và RMS (để phát hiện câm/méo), không lưu âm thanh."""
    import array
    dec = opuslib_next.Decoder(RATE, 1)
    pcm = b"".join(dec.decode(f, FRAME_SAMPLES) for f in frames)
    samples = array.array("h", pcm)
    rms = (sum(x * x for x in samples) / max(len(samples), 1)) ** 0.5
    clipped = sum(1 for x in samples if abs(x) >= 32760)
    return f"{len(frames)} khung = {len(samples) / RATE:.1f}s, RMS {rms:.0f}, mẫu chạm trần {clipped}"


async def main() -> None:
    text = sys.argv[1] if len(sys.argv) > 1 else "I like swimming"
    runs = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    pcm = await synth(text)
    speech = opus_frames(pcm)
    silence = opus_frames(b"\x00" * int(RATE * 2 * SILENCE_S))
    print(f"Câu thử: {text!r} ({len(speech) * FRAME_MS / 1000:.1f}s âm thanh)")
    res = []
    for i in range(runs):
        r = await one_turn(speech, silence)
        res.append(r)
        fa = f"{r['first_audio']:.2f}s" if r["first_audio"] is not None else "KHÔNG CÓ ÂM THANH"
        st = f"{r['stt']:.2f}s" if r["stt"] is not None else "-"
        print(f"  lượt {i + 1}: stt {st} | âm thanh đầu {fa} | nhận dạng: {r['text']!r}")
        if i == runs - 1 and r["frames"]:
            print("  âm thanh nhận được:", audio_stats(r["frames"]))
    ok = [r["first_audio"] for r in res[1:] if r["first_audio"] is not None]  # bỏ lượt đầu (khởi động)
    if ok:
        print(f"Từ lúc nói xong tới âm thanh đầu (bỏ lượt 1, {len(ok)} lượt): trung vị {statistics.median(ok):.2f}s, max {max(ok):.2f}s")


asyncio.run(main())
