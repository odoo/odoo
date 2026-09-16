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


# psycopg_pool's own `_shrink_pool` minus its "unused for max_idle" rule:
# the oldest idle connections go, under the pool's lock, never below
# min_size. `tests/contract/test_psycopg_pool_internals.py` pins the four
# attributes this reads against the installed psycopg_pool.
def close_idle_connections(pool, count: int) -> int:
    to_close: list[Any] = []
    with pool._lock:
        while len(to_close) < count and pool._pool and pool._nconns > pool.min_size:
            to_close.append(pool._pool.popleft())
            pool._nconns -= 1
        pool._nconns_min = min(pool._nconns_min, len(pool._pool))
    for conn in to_close:
        pool._close_connection(conn)
    return len(to_close)


# One process's backends against one server are bounded by the budget only
# while checked out; each per-database pool keeps its own idle ones, so a
# host serving many databases holds up to maxconn x databases at rest.
# Trim on return, least recently borrowed pool first, until the pools of
# this ConnectionPool hold no more than `ceiling` connections in total.
def trim_idle_to_ceiling(pools: Mapping[Any, Any], ceiling: int) -> int:
    excess = sum(pool._nconns for pool in pools.values()) - ceiling
    if excess <= 0:
        return 0
    trimmed = 0
    now = monotonic()
    for pool in sorted(
        pools.values(), key=lambda pool: getattr(pool, _LAST_BORROW_ATTR, now)
    ):
        trimmed += close_idle_connections(pool, excess - trimmed)
        if trimmed >= excess:
            break
    _debug.lifecycle(
        "pool.trimmed_to_ceiling",
        ceiling=ceiling,
        excess=excess,
        trimmed=trimmed,
        pools=len(pools),
    )
    return trimmed


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
