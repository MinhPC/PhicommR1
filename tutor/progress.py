"""Tiến độ học bằng SQLite (WAL). Mọi truy vấn lọc theo child_id."""
from __future__ import annotations

import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, List, Optional

MISTAKE_TYPES = ("grammar", "vocab", "pronunciation")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions(
  id INTEGER PRIMARY KEY, child_id TEXT NOT NULL, device_id TEXT,
  started_at INTEGER NOT NULL, ended_at INTEGER, mode TEXT,
  minutes REAL DEFAULT 0, cost_usd REAL DEFAULT 0);
CREATE TABLE IF NOT EXISTS mistakes(
  id INTEGER PRIMARY KEY, child_id TEXT NOT NULL, session_id INTEGER,
  type TEXT NOT NULL CHECK(type IN ('grammar','vocab','pronunciation')),
  said TEXT, correct TEXT, word TEXT, score REAL, created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS vocab_seen(
  child_id TEXT NOT NULL, word TEXT NOT NULL, unit INTEGER,
  times_seen INTEGER NOT NULL DEFAULT 0, times_correct INTEGER NOT NULL DEFAULT 0,
  last_seen INTEGER, PRIMARY KEY(child_id, word));
CREATE TABLE IF NOT EXISTS stories(
  id INTEGER PRIMARY KEY, series TEXT, episode INTEGER, level INTEGER, title TEXT,
  file_path TEXT, transcript_path TEXT, duration_s REAL, added_at INTEGER, order_index INTEGER);
CREATE TABLE IF NOT EXISTS listens(
  id INTEGER PRIMARY KEY, child_id TEXT NOT NULL, story_id INTEGER NOT NULL,
  started_at INTEGER, seconds_played REAL DEFAULT 0, completed INTEGER DEFAULT 0,
  quiz_correct INTEGER DEFAULT 0, quiz_total INTEGER DEFAULT 0);
CREATE INDEX IF NOT EXISTS ix_mistakes_child ON mistakes(child_id, created_at);
CREATE INDEX IF NOT EXISTS ix_sessions_child ON sessions(child_id, started_at);
"""


class Progress:
    def __init__(self, path: str | Path):
        self._path = str(path)
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.execute("PRAGMA journal_mode=WAL")  # hai phiên ghi song song
            c.executescript(SCHEMA)

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        c = sqlite3.connect(self._path, timeout=10)
        c.row_factory = sqlite3.Row
        try:
            with c:  # commit/rollback
                yield c
        finally:
            c.close()

    def start_session(self, child_id: str, device_id: str, mode: str = "free_chat") -> int:
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO sessions(child_id, device_id, started_at, mode) VALUES(?,?,?,?)",
                (child_id, device_id, int(time.time()), mode))
            return int(cur.lastrowid)

    def end_session(self, session_id: int, minutes: float, cost_usd: float = 0.0) -> None:
        with self._conn() as c:
            c.execute("UPDATE sessions SET ended_at=?, minutes=?, cost_usd=? WHERE id=?",
                      (int(time.time()), minutes, cost_usd, session_id))

    def add_mistake(self, child_id: str, session_id: Optional[int], type_: str, said: str,
                    correct: str = "", word: Optional[str] = None,
                    score: Optional[float] = None) -> None:
        if type_ not in MISTAKE_TYPES:
            raise ValueError(f"type phải là một trong {MISTAKE_TYPES}, nhận {type_!r}")
        with self._conn() as c:
            c.execute(
                "INSERT INTO mistakes(child_id, session_id, type, said, correct, word, score, created_at)"
                " VALUES(?,?,?,?,?,?,?,?)",
                (child_id, session_id, type_, said, correct, word, score, int(time.time())))

    def mark_word(self, child_id: str, word: str, unit: Optional[int], correct: bool) -> None:
        word = word.strip().lower()
        now = int(time.time())
        with self._conn() as c:
            c.execute(
                "INSERT INTO vocab_seen(child_id, word, unit, times_seen, times_correct, last_seen)"
                " VALUES(?,?,?,1,?,?)"
                " ON CONFLICT(child_id, word) DO UPDATE SET"
                " times_seen=times_seen+1, times_correct=times_correct+excluded.times_correct,"
                " last_seen=excluded.last_seen, unit=COALESCE(excluded.unit, unit)",
                (child_id, word, unit, 1 if correct else 0, now))

    def weak_words(self, child_id: str, limit: int = 10) -> List[str]:
        """Từ bé hay sai gần đây nhất (không trùng), dùng cho prompt và chế độ Review."""
        with self._conn() as c:
            rows = c.execute(
                "SELECT word, MAX(created_at) AS t FROM mistakes"
                " WHERE child_id=? AND word IS NOT NULL AND word<>''"
                " GROUP BY word ORDER BY t DESC, MAX(id) DESC LIMIT ?",
                (child_id, limit)).fetchall()
        return [r["word"] for r in rows]

    def session_minutes_today(self, child_id: str) -> float:
        lt = time.localtime()  # giờ địa phương của máy chạy server, không phải UTC
        start_of_day = int(time.mktime((lt.tm_year, lt.tm_mon, lt.tm_mday, 0, 0, 0, 0, 0, -1)))
        with self._conn() as c:
            row = c.execute("SELECT COALESCE(SUM(minutes),0) AS m FROM sessions"
                            " WHERE child_id=? AND started_at>=?", (child_id, start_of_day)).fetchone()
        return float(row["m"])
