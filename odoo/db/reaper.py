from __future__ import annotations

import threading
from time import monotonic
from typing import TYPE_CHECKING, Any

from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from collections.abc import Mapping

_LAST_BORROW_ATTR = "_odoo_last_borrow"
_debug = DebugLog(__name__)


def mark_active(pool) -> None:
    setattr(pool, _LAST_BORROW_ATTR, monotonic())


def get_checked_out_count(pool) -> int:
    stats = pool.get_stats()
    return stats.get("pool_size", 0) - stats.get("pool_available", 0)


class IdlePoolReaper:
    __slots__ = ("_last_check", "check_interval", "ttl")

    def __init__(self, ttl: float):
        self.ttl = ttl
        self.check_interval = max(1.0, ttl / 4) if ttl > 0 else 0.0
        self._last_check = 0.0
        _debug.lifecycle(
            "pool.reaper_created", ttl=ttl, check_interval=self.check_interval
        )

    @property
    def enabled(self) -> bool:
        return self.ttl > 0

    def acquire_check_interval(self) -> bool:
        if self.check_interval <= 0:
            return False
        now = monotonic()
        if now - self._last_check < self.check_interval:
            return False
        self._last_check = now
        return True

    def is_probably_due(self) -> bool:
        if self.check_interval <= 0:
            return False
        return monotonic() - self._last_check >= self.check_interval

    def get_keys_reapable(
        self, pools: Mapping[Any, Any], exclude_key: Any = None
    ) -> list:
        if not self.enabled:
            return []
        now = monotonic()
        reapable = []
        for key, pool in pools.items():
            if key == exclude_key:
                continue
            if now - getattr(pool, _LAST_BORROW_ATTR, now) <= self.ttl:
                continue
            checked_out = get_checked_out_count(pool)
            if checked_out > 0:
                _debug.logic(
                    "pool.reap_deferred",
                    reason="checked_out",
                    idle_s=now - getattr(pool, _LAST_BORROW_ATTR, now),
                    checked_out=checked_out,
                )
                continue
            reapable.append(key)
        _debug.pipeline(
            "pool.reap_scan", pools=len(pools), reapable=len(reapable), ttl=self.ttl
        )
        return reapable

    @staticmethod
    def close_pools_in_background(target, pools: list, name: str) -> None:
        _debug.lifecycle("pool.reaper_thread_started", count=len(pools), name=name)
        threading.Thread(target=target, args=(pools,), name=name, daemon=True).start()
