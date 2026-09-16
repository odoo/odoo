from __future__ import annotations

import threading
from time import monotonic
from typing import Any, NamedTuple

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class Checkout(NamedTuple):
    since: float
    thread: str
    caller: str | None

    def get_age(self) -> float:
        return monotonic() - self.since

    def describe(self) -> str:
        where = f" at {self.caller}" if self.caller else ""
        return f"{self.get_age():.1f}s by {self.thread}{where}"


class CheckoutTracker:
    __slots__ = ("_last_report", "_out", "_report_lock")

    def __init__(self) -> None:
        self._out: dict[object, Checkout] = {}
        self._last_report = 0.0
        self._report_lock = threading.Lock()

    def track(self, conn: object, caller: str | None = None) -> None:
        self._out[conn] = Checkout(monotonic(), threading.current_thread().name, caller)

    def release(self, conn: object) -> float | None:
        entry = self._out.pop(conn, None)
        return None if entry is None else entry.get_age()

    def __len__(self) -> int:
        return len(self._out)

    def get_connections_of(self, thread_name: str) -> list[Any]:
        return [
            conn
            for conn, entry in self._out.copy().items()
            if entry.thread == thread_name
        ]

    def is_held_by(self, conn: object, thread_name: str) -> bool:
        entry = self._out.get(conn)
        return entry is not None and entry.thread == thread_name

    def get_checkouts_outstanding(self, older_than: float = 0.0) -> list[Checkout]:
        return sorted(
            (c for c in self._out.copy().values() if c.get_age() > older_than),
            key=lambda c: c.since,
        )

    def get_oldest_age(self) -> float:
        entries = self._out.copy().values()
        return max((c.get_age() for c in entries), default=0.0)

    def acquire_report_interval(self, interval: float) -> bool:
        now = monotonic()
        with self._report_lock:
            if now - self._last_report < interval:
                _debug.logic(
                    "leaks.report_throttled",
                    interval=interval,
                    since_last_s=now - self._last_report,
                    outstanding=len(self._out),
                )
                return False
            self._last_report = now
            return True

    def describe(self, limit: int = 3, older_than: float = 0.0) -> str:
        held = self.get_checkouts_outstanding(older_than)
        _debug.logic(
            "leaks.described",
            older_than=older_than,
            held=len(held),
            outstanding=len(self._out),
            oldest_s=held[0].get_age() if held else 0.0,
        )
        if not held:
            return ""
        shown = "; ".join(c.describe() for c in held[:limit])
        more = f" (+{len(held) - limit} more)" if len(held) > limit else ""
        return f"oldest checkouts: {shown}{more}"
