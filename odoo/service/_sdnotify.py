from __future__ import annotations

import os
import socket
import time

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

__all__ = (
    "Watchdog",
    "get_watchdog_interval",
    "notify",
    "notify_ready",
    "notify_reloading",
)


def _get_notify_socket() -> str | None:
    path = os.environ.get("NOTIFY_SOCKET") or ""
    if not path:
        return None
    # An abstract socket is spelled with a leading "@" in the variable.
    return "\0" + path[1:] if path.startswith("@") else path


def notify(state: str) -> bool:
    path = _get_notify_socket()
    if path is None:
        return False
    try:
        with socket.socket(
            socket.AF_UNIX, socket.SOCK_DGRAM | socket.SOCK_CLOEXEC
        ) as s:
            s.connect(path)
            s.sendall(state.encode())
    except OSError as exc:
        _debug.logic(
            "sdnotify.failed", state=state.split("=", 1)[0], error=type(exc).__name__
        )
        return False
    _debug.lifecycle("sdnotify.sent", state=state.split("\n", 1)[0])
    return True


def notify_ready() -> bool:
    return notify("READY=1")


def notify_reloading() -> bool:
    # Type=notify-reload wants the CLOCK_MONOTONIC stamp of the request.
    return notify(f"RELOADING=1\nMONOTONIC_USEC={time.monotonic_ns() // 1000}")


def get_watchdog_interval() -> float | None:
    # Half of the unit's WatchdogSec=, as sd_watchdog_enabled(3) recommends,
    # and only when the variable names this process or names none.
    usec = os.environ.get("WATCHDOG_USEC") or ""
    if not usec.isdigit():
        return None
    pid = os.environ.get("WATCHDOG_PID") or ""
    if pid and pid != str(os.getpid()):
        return None
    return int(usec) / 1_000_000 / 2


class Watchdog:
    """Sends WATCHDOG=1 at half the unit's WatchdogSec=, from a loop that
    already wakes on its own schedule; `bound()` shortens a sleep so the
    next beat is not missed."""

    __slots__ = ("_interval", "_last")

    def __init__(self) -> None:
        self._interval = get_watchdog_interval()
        self._last = float("-inf")

    @property
    def enabled(self) -> bool:
        return self._interval is not None

    def beat(self) -> bool:
        if self._interval is None:
            return False
        now = time.monotonic()
        if now - self._last < self._interval:
            return False
        self._last = now
        return notify("WATCHDOG=1")

    def bound(self, sleep_s: float) -> float:
        if self._interval is None:
            return sleep_s
        return max(0.0, min(sleep_s, self._interval - (time.monotonic() - self._last)))
