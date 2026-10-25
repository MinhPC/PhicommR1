import os
import textwrap

import pytest

from tutor.children import ChildRegistry, ConfigError, normalize_device_id

BASE = textwrap.dedent("""
    children:
      - {id: be_a, name: An, level: 2, book: gs, current_unit: 5, little_fox_level: 2}
      - {id: be_b, name: Binh, level: 1, book: gs, current_unit: 3, daily_minutes: {talk: 10, story: 20}}
    devices:
      "FC:7C:02:57:7C:0B": {child: be_a, type: r1, has_screen: false}
      "32-83-a0-82-68-c4": {child: be_b, type: esp32, has_screen: true}
""")


def write(path, text, bump=0):
    path.write_text(text, encoding="utf-8")
    st = path.stat()
    os.utime(path, (st.st_atime, st.st_mtime + bump))


@pytest.fixture
def cfg(tmp_path):
    p = tmp_path / "children.yaml"
    write(p, BASE)
    return p


def test_normalize():
    assert normalize_device_id(" FC-7C:02:57:7C:0B ") == "fc:7c:02:57:7c:0b"


def test_lookup_ignores_case_and_separator(cfg):
    reg = ChildRegistry(cfg)
    assert reg.child_for_device("fc:7c:02:57:7c:0b").id == "be_a"
    assert reg.child_for_device("32:83:A0:82:68:C4").id == "be_b"
    assert reg.device("32:83:a0:82:68:c4").has_screen is True


def test_defaults_and_minutes(cfg):
    reg = ChildRegistry(cfg)
    b = reg.child("be_b")
    assert (b.talk_minutes, b.story_minutes) == (10, 20)
    assert b.little_fox_level == 1  # mặc định = level
    assert reg.child("be_a").talk_minutes == 15


def test_unknown_device_is_guest(cfg):
    assert ChildRegistry(cfg).child_for_device("aa:bb:cc:dd:ee:ff") is None


def test_hot_reload_swaps_devices(cfg):
    reg = ChildRegistry(cfg)
    swapped = BASE.replace("FC:7C:02:57:7C:0B", "TMP").replace("32-83-a0-82-68-c4", "FC:7C:02:57:7C:0B") \
                  .replace("TMP", "32-83-a0-82-68-c4")
    write(cfg, swapped, bump=5)
    assert reg.child_for_device("fc:7c:02:57:7c:0b").id == "be_b"


def test_bad_reload_keeps_old_config(cfg):
    reg = ChildRegistry(cfg)
    write(cfg, "children: [", bump=5)  # YAML hỏng
    assert reg.child_for_device("fc:7c:02:57:7c:0b").id == "be_a"


@pytest.mark.parametrize("patch,msg", [
    ("level: 2", "level: 9"),
])
def test_invalid_level_rejected(tmp_path, patch, msg):
    p = tmp_path / "c.yaml"
    write(p, BASE.replace(patch, msg, 1))
    with pytest.raises(ConfigError):
        ChildRegistry(p)


def test_device_pointing_to_missing_child_rejected(tmp_path):
    p = tmp_path / "c.yaml"
    write(p, BASE.replace("child: be_b", "child: ghost"))
    with pytest.raises(ConfigError):
        ChildRegistry(p)
