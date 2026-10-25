import pytest

from tutor.commands import Command, detect_command


@pytest.mark.parametrize("text,expected", [
    ("Let's learn unit 5", Command("lesson", 5)),
    ("let’s learn unit 12.", Command("lesson", 12)),   # dấu nháy cong + dấu chấm
    ("Lets learn unit 3", Command("lesson", 3)),
    ("Let's practice speaking", Command("repeat")),
    ("Let's review", Command("review")),
    ("Talk time!", Command("talk_time")),
    ("Story time", Command("story")),
    ("Quiz time for two", Command("quiz_two")),
    ("Goodbye", Command("goodbye")),
    ("Bye bye.", Command("goodbye")),
    ("Next story", Command("next_story")),
    ("Play it again", Command("replay")),
    ("Louder", Command("louder")),
    ("Quieter", Command("quieter")),
    ("Stop", Command("stop")),
])
def test_detects(text, expected):
    assert detect_command(text) == expected


@pytest.mark.parametrize("text", [
    "",
    "   ",
    "I don't want to stop playing",      # "stop" nằm trong câu dài → không phải lệnh
    "my favorite story is the fox",
    "I like swimming",
    "tôi muốn học bài 5",                # tiếng Việt không khớp
])
def test_ignores_normal_speech(text):
    assert detect_command(text) is None


def test_command_inside_longer_sentence_for_modes():
    assert detect_command("Okay, can we have story time now") == Command("story")
