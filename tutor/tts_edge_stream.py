"""Provider TTS `edge_stream` cho xiaozhi-server. Được mount vào core/providers/tts/edge_stream.py.

TUTOR-PATCH: ghi đè `to_tts_stream` để phát Opus dần; mọi thứ khác dùng lại provider `edge` của upstream.
"""
import asyncio

from config.logger import setup_logging
from core.providers.tts.dto.dto import SentenceType
from core.providers.tts.edge import TTSProvider as EdgeProvider
from core.utils.tts import MarkdownCleaner
from tutor.edge_stream_core import NoAudio, stream_edge_to_opus

TAG = __name__
logger = setup_logging()
MAX_TRIES = 5


class TTSProvider(EdgeProvider):
    def to_tts_stream(self, text, opus_handler=None) -> None:
        original = text
        text = MarkdownCleaner.clean_markdown(text)
        if self._correct_words_pattern:
            text = self._correct_words_pattern.sub(lambda m: self.correct_words[m.group(0)], text)

        sentence_id = getattr(self, "current_sentence_id", None)
        started = {"v": False}

        def on_first():
            started["v"] = True
            self.tts_audio_queue.put((SentenceType.FIRST, None, original, sentence_id))

        for attempt in range(1, MAX_TRIES + 1):
            try:
                asyncio.run(stream_edge_to_opus(
                    text, voice=self.voice, rate=self.edge_rate, volume=self.edge_volume,
                    pitch=self.edge_pitch, sample_rate=self.conn.sample_rate,
                    encoder=self.opus_encoder, on_opus=opus_handler, on_first=on_first))
                logger.bind(tag=TAG).info(f"语音生成成功: {original}，重试{attempt - 1}次")
                return None
            except NoAudio as e:
                logger.bind(tag=TAG).warning(f"语音生成失败{attempt}次: {original}，错误: {e}")
            except Exception as e:
                if started["v"]:  # đã phát một phần: thử lại sẽ lặp âm thanh, nên dừng
                    logger.bind(tag=TAG).error(f"语音生成中断(已发出部分音频): {original}，错误: {e}")
                    return None
                logger.bind(tag=TAG).warning(f"语音生成失败{attempt}次: {original}，错误: {e}")
        logger.bind(tag=TAG).error(f"语音生成失败: {original}，请检查网络或服务是否正常")
        return None
