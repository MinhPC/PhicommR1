import re

import pytest

from tutor.children import Child
from tutor.prompt import COMMON, build_system_prompt, tts_rate


def child(level=2, name="An"):
    return Child("be_a", name, level, "gs", 5, level, 15, 15)


UNIT = {"title": "Our hobbies", "vocabulary": ["swimming", "singing"], "patterns": ["I like {hobby}."]}


def test_contains_name_unit_and_weak_words():
    p = build_system_prompt(child(), UNIT, ["cat", "three"])
    assert "An" in p and "Our hobbies" in p and "swimming" in p
    assert "cat, three" in p


def test_level_changes_sentence_length():
    low = build_system_prompt(child(1))
    high = build_system_prompt(child(5))
    assert "3 to 6 words" in low and "8 to 12 words" in high


def test_weak_words_capped_at_ten():
    p = build_system_prompt(child(), None, [f"w{i}" for i in range(20)])
    assert "w9" in p and "w10" not in p


def test_no_comparison_between_children():
    p = build_system_prompt(child(), UNIT, ["x"])
    assert "Never compare" in p
    assert not re.search(r"brother|twin", p, re.I)


def test_prompt_stays_short():
    # Prompt dài làm tăng trễ và tiền ở mọi lượt (spec A10); chặn tăng vô ý.
    assert len(build_system_prompt(child(), UNIT, ["a"] * 10).split()) < 200


@pytest.mark.parametrize("level,rate", [(1, "-15%"), (2, "-15%"), (5, "+0%")])
def test_tts_rate(level, rate):
    assert tts_rate(level) == rate


def test_common_forbids_emoji_and_personal_questions():
    assert "no emoji" in COMMON and "personal information" in COMMON
