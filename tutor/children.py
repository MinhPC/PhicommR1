"""Hồ sơ trẻ và gắn thiết bị (data/children.yaml), tự đọc lại khi file đổi."""
from __future__ import annotations

import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

import yaml

log = logging.getLogger("tutor.children")

MIN_LEVEL, MAX_LEVEL = 1, 5


def normalize_device_id(raw: str) -> str:
    """MAC/device-id viết thường, dùng dấu hai chấm."""
    return str(raw).strip().lower().replace("-", ":")


@dataclass(frozen=True)
class Child:
    id: str
    name: str
    level: int
    book: str
    current_unit: int
    little_fox_level: int
    talk_minutes: int
    story_minutes: int


@dataclass(frozen=True)
class Device:
    device_id: str
    child_id: str
    type: str
    has_screen: bool


class ConfigError(ValueError):
    pass


def _parse(data: dict) -> tuple[Dict[str, Child], Dict[str, Device]]:
    children: Dict[str, Child] = {}
    for c in data.get("children") or []:
        cid = str(c["id"])
        if cid in children:
            raise ConfigError(f"trùng id bé: {cid}")
        level = int(c["level"])
        if not MIN_LEVEL <= level <= MAX_LEVEL:
            raise ConfigError(f"{cid}: level phải từ {MIN_LEVEL} đến {MAX_LEVEL}, nhận {level}")
        minutes = c.get("daily_minutes") or {}
        children[cid] = Child(
            id=cid,
            name=str(c["name"]),
            level=level,
            book=str(c["book"]),
            current_unit=int(c["current_unit"]),
            little_fox_level=int(c.get("little_fox_level", level)),
            talk_minutes=int(minutes.get("talk", 15)),
            story_minutes=int(minutes.get("story", 15)),
        )

    devices: Dict[str, Device] = {}
    for raw_id, d in (data.get("devices") or {}).items():
        did = normalize_device_id(raw_id)
        if did in devices:
            raise ConfigError(f"trùng device_id: {did}")
        if d["child"] not in children:
            raise ConfigError(f"thiết bị {did} trỏ tới bé không tồn tại: {d['child']}")
        devices[did] = Device(
            device_id=did,
            child_id=d["child"],
            type=str(d.get("type", "unknown")),
            has_screen=bool(d.get("has_screen", False)),
        )
    return children, devices


class ChildRegistry:
    """Đọc children.yaml; mỗi lần tra cứu kiểm tra mtime để reload không cần restart."""

    def __init__(self, path: str | os.PathLike):
        self._path = Path(path)
        self._lock = threading.Lock()
        self._mtime: Optional[float] = None
        self._children: Dict[str, Child] = {}
        self._devices: Dict[str, Device] = {}
        self._warned: set[str] = set()
        self._reload(force=True)

    def _reload(self, force: bool = False) -> None:
        mtime = self._path.stat().st_mtime
        if not force and mtime == self._mtime:
            return
        with open(self._path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        children, devices = _parse(data)  # lỗi cấu hình mới → giữ cấu hình cũ
        self._children, self._devices, self._mtime = children, devices, mtime
        log.info("Đã nạp %d bé, %d thiết bị", len(children), len(devices))

    def _refresh(self) -> None:
        with self._lock:
            try:
                self._reload()
            except Exception as e:  # giữ cấu hình cũ nếu file đang sửa dở
                log.error("Không nạp lại được %s, giữ cấu hình cũ: %s", self._path, e)

    def child(self, child_id: str) -> Child:
        self._refresh()
        return self._children[child_id]

    def device(self, device_id: str) -> Optional[Device]:
        self._refresh()
        return self._devices.get(normalize_device_id(device_id))

    def child_for_device(self, device_id: str) -> Optional[Child]:
        """None = thiết bị lạ → chế độ khách (không ghi progress)."""
        dev = self.device(device_id)
        if dev is None:
            key = normalize_device_id(device_id)
            if key not in self._warned:  # chỉ cảnh báo một lần mỗi thiết bị
                self._warned.add(key)
                log.warning("Thiết bị chưa có trong children.yaml (chế độ khách): %s", key)
            return None
        return self._children[dev.child_id]
