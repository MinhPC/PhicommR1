from pathlib import Path

import pytest
import yaml

from tutor.tools.gen_config import build_config

UPSTREAM = Path(__file__).resolve().parents[2] / "upstream" / "main" / "xiaozhi-server" / "config.yaml"
FAKE = {"OPENAI_API_KEY": "sk-test-not-real"}


def cfg():
    return build_config(FAKE, "192.168.31.96")


def test_timezone_offset_is_number():
    assert isinstance(cfg()["server"]["timezone_offset"], int)


def test_urls_use_given_host():
    s = cfg()["server"]
    assert s["websocket"] == "ws://192.168.31.96:8000/xiaozhi/v1/"
    assert s["vision_explain"].startswith("http://192.168.31.96:8003/")


def test_vad_silence_not_lowered_below_spec():
    # Spec: trẻ ngập ngừng khi nói tiếng Anh, không hạ dưới ~800 ms.
    assert cfg()["VAD"]["SileroVAD"]["min_silence_duration_ms"] >= 800


def test_selected_modules_are_all_defined():
    c = cfg()
    for kind in ("ASR", "LLM", "TTS", "VAD"):
        assert c["selected_module"][kind] in c[kind]


@pytest.mark.skipif(not UPSTREAM.exists(), reason="chưa có upstream/ để đối chiếu")
def test_module_names_exist_in_upstream_config():
    up = yaml.safe_load(UPSTREAM.read_text(encoding="utf-8"))
    sel = cfg()["selected_module"]
    for kind in ("VAD", "ASR", "TTS"):
        assert sel[kind] in up[kind], f"{kind}.{sel[kind]} không có trong config upstream"
    # LLM là mục do ta tự định nghĩa (tên tuỳ ý); chỉ `type` phải có trình điều khiển trong upstream.
    llm_type = cfg()["LLM"][sel["LLM"]]["type"]
    assert (UPSTREAM.parent / "core" / "providers" / "llm" / llm_type).exists(), f"không có provider llm/{llm_type}"
    assert sel["Intent"] in up["Intent"] and sel["Memory"] in up["Memory"]


@pytest.mark.skipif(not UPSTREAM.exists(), reason="chưa có upstream/ để đối chiếu")
def test_override_keys_exist_in_upstream():
    up = yaml.safe_load(UPSTREAM.read_text(encoding="utf-8"))
    c = cfg()
    for key in ("server", "log", "prompt_template", "prompt", "enable_greeting"):
        assert key in up, f"khoá gốc {key!r} không có trong config upstream"
    for k in c["server"]:
        assert k in up["server"], f"server.{k} không có trong config upstream"
    # Mỗi khoá ghi đè trong module đã chọn phải có sẵn trong mục tương ứng của upstream.
    for kind, name in (("VAD", "SileroVAD"), ("ASR", "FunASR")):
        for k in c[kind][name]:
            assert k in up[kind][name], f"{kind}.{name}.{k} không có trong config upstream"
    for k in c["TTS"]["EdgeTTS"]:
        assert k in up["TTS"]["EdgeTTS"] or k == "language", f"TTS.EdgeTTS.{k} lạ"


def test_key_not_in_prompt():
    assert "sk-test" not in cfg()["prompt"]


ROOT = Path(__file__).resolve().parents[2]


def test_tts_type_is_edge_stream_and_provider_is_mounted():
    # type `edge_stream` chỉ tìm được nếu file provider được mount đúng tên vào core/providers/tts/.
    assert cfg()["TTS"]["EdgeTTS"]["type"] == "edge_stream"
    assert (ROOT / "tutor" / "tts_edge_stream.py").exists()
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "tts_edge_stream.py:/opt/xiaozhi-esp32-server/core/providers/tts/edge_stream.py" in compose


@pytest.mark.skipif(not UPSTREAM.exists(), reason="chưa có upstream/ để đối chiếu")
def test_overridden_tts_hook_exists_upstream():
    # Provider của ta ghi đè to_tts_stream; nếu upstream đổi tên hàm này thì phải biết ngay.
    base = (UPSTREAM.parent / "core" / "providers" / "tts" / "base.py").read_text(encoding="utf-8")
    assert "def to_tts_stream(self, text, opus_handler" in base
    assert "encode_pcm_to_opus_stream" in (UPSTREAM.parent / "core" / "utils" / "opus_encoder_utils.py").read_text(encoding="utf-8")
