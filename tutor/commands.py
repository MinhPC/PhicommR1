"""Nhận diện lệnh giọng nói bằng từ khoá trên transcript, không tốn lượt LLM."""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

# Lệnh điều khiển ngắn: chỉ nhận khi CẢ CÂU khớp, để "I don't want to stop" không bị tính là lệnh.
_SHORT_CONTROL = {
    "stop": "stop",
    "louder": "louder",
    "quieter": "quieter",
    "next story": "next_story",
    "play it again": "replay",
    "goodbye": "goodbye",
    "good bye": "goodbye",
    "bye bye": "goodbye",
}

_PATTERNS = [
    ("lesson", re.compile(r"\blet'?s learn unit (\d{1,2})\b")),
    ("repeat", re.compile(r"\blet'?s practi[cs]e speaking\b")),
    ("review", re.compile(r"\blet'?s review\b")),
    ("talk_time", re.compile(r"\btalk time\b")),
    ("story", re.compile(r"\bstory time\b")),
    ("quiz_two", re.compile(r"\bquiz time for two\b")),
]


@dataclass(frozen=True)
class Command:
    kind: str
    arg: Optional[int] = None


def _normalize(text: str) -> str:
    t = text.lower().replace("’", "'").replace("‘", "'")
    t = re.sub(r"[^a-z0-9' ]+", " ", t)  # bỏ dấu câu; ASR tiếng Việt có dấu → không khớp, đúng ý
    return re.sub(r"\s+", " ", t).strip()


def detect_command(transcript: str) -> Optional[Command]:
    t = _normalize(transcript)
    if not t:
        return None
    if t in _SHORT_CONTROL:
        return Command(_SHORT_CONTROL[t])
    for kind, pat in _PATTERNS:
        m = pat.search(t)
        if m:
            return Command(kind, int(m.group(1)) if m.groups() else None)
    return None
