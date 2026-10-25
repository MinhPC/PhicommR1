"""Edge TTS streaming: mp3 -> ffmpeg (chạy liên tục) -> PCM -> Opus, gọi on_opus ngay khi có khung.

Không import gì từ mã upstream để kiểm thử độc lập. Lý do tồn tại: upstream gom cả câu mp3 rồi mới
đổi sang Opus (~0,7 s trước khung đầu, xem CLAUDE.md A5). Ở đây khung đầu ra ngay khi vài khối mp3 đầu tới.
"""
from __future__ import annotations

import asyncio
from typing import Callable, Optional

FFMPEG_ARGS = ("-loglevel", "error", "-nostdin",
               "-probesize", "32", "-analyzeduration", "0", "-fflags", "nobuffer",  # đừng chờ dò định dạng
               "-f", "mp3", "-i", "pipe:0")


class NoAudio(RuntimeError):
    """Không có mẫu PCM nào được tạo (cho phép thử lại an toàn vì chưa phát gì)."""


async def stream_edge_to_opus(
    text: str, *, voice: str, rate: str, volume: str, pitch: str, sample_rate: int,
    encoder, on_opus: Callable[[bytes], None], on_first: Optional[Callable[[], None]] = None,
    ffmpeg: str = "ffmpeg",
) -> int:
    """Trả về số byte PCM đã phát. Ném NoAudio nếu chưa phát được gì (an toàn để thử lại)."""
    import edge_tts  # nhập muộn: chỉ có trong container

    proc = await asyncio.create_subprocess_exec(
        ffmpeg, *FFMPEG_ARGS, "-f", "s16le", "-ar", str(sample_rate), "-ac", "1", "pipe:1",
        stdin=asyncio.subprocess.PIPE, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)

    async def feed() -> None:
        try:
            comm = edge_tts.Communicate(text, voice=voice, rate=rate, volume=volume, pitch=pitch)
            async for ch in comm.stream():
                if ch["type"] == "audio":
                    proc.stdin.write(ch["data"])
                    await proc.stdin.drain()
        finally:
            try:
                proc.stdin.close()
            except Exception:
                pass

    feeder = asyncio.create_task(feed())
    total, carry, first = 0, b"", True
    try:
        while True:
            data = await proc.stdout.read(4096)
            if not data:
                break
            data = carry + data
            if len(data) % 2:                       # giữ nguyên ranh giới mẫu 16-bit
                data, carry = data[:-1], data[-1:]
            else:
                carry = b""
            if not data:
                continue
            if first:
                first = False
                if on_first:
                    on_first()
            encoder.encode_pcm_to_opus_stream(data, False, on_opus)
            total += len(data)
        await feeder                                 # nếu Edge lỗi, ngoại lệ nổi lên ở đây
        if total == 0:
            err = (await proc.stderr.read()).decode(errors="replace")[:200]
            raise NoAudio(f"không có âm thanh (ffmpeg: {err or 'im lặng'})")
        encoder.encode_pcm_to_opus_stream(b"", True, on_opus)  # đẩy khung cuối (đệm 0)
        return total
    except BaseException:
        if not feeder.done():
            feeder.cancel()
        raise
    finally:
        if proc.returncode is None:
            proc.kill()
        await proc.wait()
