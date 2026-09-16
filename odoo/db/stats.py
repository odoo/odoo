from __future__ import annotations

import threading
from bisect import bisect_left
from time import monotonic

from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)

_WAIT_BUCKETS: tuple[float, ...] = (0.001, 0.01, 0.1, 1.0, 5.0, 30.0)

_COUNTERS: dict[str, str] = {
    "borrows": "borrows",
    "borrows_direct": "borrows_direct",
    "borrows_failed": "borrows_failed",
    "borrow_wait_total": "borrow_wait_seconds_total",
    "borrow_wait_max": "borrow_wait_seconds_max",
    "pools_created": "pools_created",
    "pools_reaped": "pools_reaped",
    "pools_evicted_stale": "pools_evicted_stale",
    "connections_discarded": "connections_discarded",
    "connections_trimmed": "connections_trimmed",
    "leaks_reported": "leaks_reported",
    "probe_run": "probe_run",
    "probe_permanent": "probe_permanent",
    "probe_transient": "probe_transient",
    "probe_skipped_proven": "probe_skipped_proven",
}

_PROBE_OUTCOMES: dict[str, str] = {
    "permanent": "probe_permanent",
    "transient": "probe_transient",
    "skipped_proven": "probe_skipped_proven",
}


class PoolStats:
    __slots__ = (
        "_lock",
        "borrow_wait_buckets",
        "borrow_wait_max",
        "borrow_wait_total",
        "borrows",
        "borrows_direct",
        "borrows_failed",
        "connections_discarded",
        "connections_trimmed",
        "leaks_reported",
        "pools_created",
        "pools_evicted_stale",
        "pools_reaped",
        "probe_permanent",
        "probe_run",
        "probe_skipped_proven",
        "probe_transient",
    )

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.borrows = 0
        self.borrows_direct = 0
        self.borrows_failed = 0
        self.borrow_wait_total = 0.0
        self.borrow_wait_max = 0.0
        self.borrow_wait_buckets = [0] * (len(_WAIT_BUCKETS) + 1)
        self.pools_created = 0
        self.pools_reaped = 0
        self.pools_evicted_stale = 0
        self.connections_discarded = 0
        self.connections_trimmed = 0
        self.leaks_reported = 0
        self.probe_run = 0
        self.probe_permanent = 0
        self.probe_transient = 0
        self.probe_skipped_proven = 0

    def record_borrow(self, started_at: float) -> None:
        waited = monotonic() - started_at
        bucket = bisect_left(_WAIT_BUCKETS, waited)
        with self._lock:
            self.borrows += 1
            self.borrow_wait_total += waited
            self.borrow_wait_max = max(self.borrow_wait_max, waited)
            self.borrow_wait_buckets[bucket] += 1

    def record_borrow_failed(self) -> None:
        with self._lock:
            self.borrows_failed += 1
            _debug.lifecycle(
                "stats.borrow_failed",
                failed=self.borrows_failed,
                borrows=self.borrows,
            )

    def record_direct_borrow(self) -> None:
        with self._lock:
            self.borrows_direct += 1

    def record_probe_started(self) -> None:
        with self._lock:
            self.probe_run += 1

    def record_probe_outcome(self, outcome: str) -> None:
        field = _PROBE_OUTCOMES[outcome]
        with self._lock:
            setattr(self, field, getattr(self, field) + 1)

    def record_pool_created(self) -> None:
        with self._lock:
            self.pools_created += 1

    def record_connections_trimmed(self, count: int) -> None:
        with self._lock:
            self.connections_trimmed += count

    def record_pools_reaped(self, count: int) -> None:
        with self._lock:
            self.pools_reaped += count

    def record_pools_evicted_stale(self, count: int) -> None:
        with self._lock:
            self.pools_evicted_stale += count

    def record_connection_discarded(self) -> None:
        with self._lock:
            self.connections_discarded += 1

    def record_leak_report(self) -> None:
        with self._lock:
            self.leaks_reported += 1

    def get_snapshot(
        self, *, budget=None, direct_out: int = 0, pools: int = 0, checkouts=None
    ) -> dict:
        with self._lock:
            buckets = list(self.borrow_wait_buckets)
            counters = {key: getattr(self, attr) for attr, key in _COUNTERS.items()}
        waits = {}
        running = 0
        for edge, count in zip(_WAIT_BUCKETS, buckets, strict=False):
            running += count
            waits[f"le_{edge}"] = running
        waits["le_+Inf"] = running + buckets[-1]
        out = {
            **counters,
            "borrow_wait_seconds_total": round(
                counters["borrow_wait_seconds_total"], 6
            ),
            "borrow_wait_seconds_max": round(counters["borrow_wait_seconds_max"], 6),
            "borrow_wait_seconds": waits,
            "direct_out": direct_out,
            "pools": pools,
        }
        if checkouts is not None:
            out["checked_out"] = len(checkouts)
            out["checked_out_oldest_seconds"] = round(checkouts.get_oldest_age(), 3)
        if budget is not None:
            out.update(budget.get_snapshot())
        _debug.perf.count(
            "stats.snapshot",
            borrows=out["borrows"],
            failed=out["borrows_failed"],
            direct=out["borrows_direct"],
            wait_max_ms=out["borrow_wait_seconds_max"] * 1000.0,
            pools=pools,
            direct_out=direct_out,
            probes=out["probe_run"],
            checked_out=out.get("checked_out"),
            budget_in_use=out.get("budget_in_use"),
        )
        return out
