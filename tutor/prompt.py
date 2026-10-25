"""Ghép prompt hệ thống gia sư từ: phần chung + khối theo level + unit + từ hay sai."""
from __future__ import annotations

from typing import Optional, Sequence

from .children import Child

COMMON = (
    "You are Miss Lily, a warm English tutor for a child in grade 3. "
    "Speak only simple English at A1 level. Use at most 2 short sentences, then ask exactly ONE question. "
    "If the child speaks Vietnamese, answer in English, give the English word, and encourage them to say it. "
    "When the child makes a mistake, praise first, then say the correct sentence once. Never explain grammar. "
    "Your words are read aloud: no emoji, no lists, no symbols. "
    "Keep content safe for children. Never ask for personal information such as address, school or full name. "
    "Never compare the child with anyone else."
)

LEVEL_BLOCKS = {
    1: "Use 3 to 6 words per sentence. Speak very simply. Give Vietnamese hints often. Praise a lot.",
    2: "Use 3 to 6 words per sentence. Give a Vietnamese hint when the child is stuck. Praise often.",
    3: "Use 5 to 8 words per sentence. Give few Vietnamese hints.",
    4: "Use 8 to 12 words per sentence. Ask open questions like Why or Tell me about. Avoid Vietnamese.",
    5: "Use 8 to 12 words per sentence. Ask open questions and follow-ups. Do not use Vietnamese.",
}

# Tốc độ đọc TTS theo level (spec: chậm hơn cho level thấp).
TTS_RATE = {1: "-15%", 2: "-15%", 3: "-5%", 4: "+0%", 5: "+0%"}


def tts_rate(level: int) -> str:
    return TTS_RATE[level]


def build_system_prompt(child: Child, unit: Optional[dict] = None,
                        weak_words: Sequence[str] = ()) -> str:
    parts = [COMMON, LEVEL_BLOCKS[child.level], f"The child's name is {child.name}."]
    if unit:
        vocab = ", ".join(unit.get("vocabulary", []))
        patterns = " | ".join(unit.get("patterns", []))
        parts.append(f"Current unit: {unit.get('title', '')}. Vocabulary: {vocab}. Sentence patterns: {patterns}.")
    if weak_words:
        parts.append("Words the child often gets wrong: " + ", ".join(weak_words[:10]) +
                     ". Use them naturally and gently.")
    return " ".join(parts)
