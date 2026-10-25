import sqlite3
import threading

import pytest

from tutor.progress import Progress


@pytest.fixture
def db(tmp_path):
    return Progress(tmp_path / "tutor.db")


def test_wal_enabled(db, tmp_path):
    c = sqlite3.connect(tmp_path / "tutor.db")
    assert c.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"


def test_mistakes_are_isolated_per_child(db):
    db.add_mistake("be_a", None, "vocab", "dog", "cat", word="cat")
    db.add_mistake("be_b", None, "pronunciation", "tri", "three", word="three", score=40)
    assert db.weak_words("be_a") == ["cat"]
    assert db.weak_words("be_b") == ["three"]


def test_weak_words_distinct_and_most_recent_first(db):
    for w in ["apple", "banana", "apple", "cherry"]:
        db.add_mistake("be_a", None, "vocab", w, w, word=w)
    assert db.weak_words("be_a") == ["cherry", "apple", "banana"]
    assert db.weak_words("be_a", limit=2) == ["cherry", "apple"]


def test_invalid_mistake_type_rejected(db):
    with pytest.raises(ValueError):
        db.add_mistake("be_a", None, "spelling", "x")


def test_mark_word_upserts_counts_per_child(db, tmp_path):
    db.mark_word("be_a", "Swimming", 5, True)
    db.mark_word("be_a", "swimming", None, False)
    db.mark_word("be_b", "swimming", 3, True)
    c = sqlite3.connect(tmp_path / "tutor.db")
    rows = dict(((r[0]), (r[1], r[2], r[3])) for r in c.execute(
        "SELECT child_id, times_seen, times_correct, unit FROM vocab_seen WHERE word='swimming'"))
    assert rows["be_a"] == (2, 1, 5)  # unit cũ được giữ khi lần sau không truyền unit
    assert rows["be_b"] == (1, 1, 3)


def test_session_minutes_today_counts_only_that_child(db):
    s1 = db.start_session("be_a", "dev1")
    db.end_session(s1, 12.5, 0.01)
    s2 = db.start_session("be_b", "dev2")
    db.end_session(s2, 3.0)
    assert db.session_minutes_today("be_a") == 12.5
    assert db.session_minutes_today("be_b") == 3.0


def test_two_sessions_write_concurrently(db):
    errors = []

    def work(child):
        try:
            for i in range(50):
                db.add_mistake(child, None, "vocab", f"w{i}", "x", word=f"w{i}")
        except Exception as e:  # pragma: no cover
            errors.append(e)

    ts = [threading.Thread(target=work, args=(c,)) for c in ("be_a", "be_b")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert not errors
    assert len(db.weak_words("be_a", limit=100)) == 50
    assert len(db.weak_words("be_b", limit=100)) == 50
