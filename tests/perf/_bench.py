from __future__ import annotations

import statistics
import threading
import time
from collections.abc import Callable
from contextlib import contextmanager


class StatementCounter:
    """Count driver submissions, with executemany treated as one submission."""

    def __init__(self) -> None:
        self.count = 0
        self._time_start = getattr(threading.current_thread(), "query_time", 0.0)

    def _record(self, cursor, query, params, start, delay):
        self.count += 1

    @property
    def seconds(self):
        return threading.current_thread().query_time - self._time_start

    @contextmanager
    def on(self):
        thread = threading.current_thread()
        owns_time = not hasattr(thread, "query_count")
        if owns_time:
            thread.query_count = 0
            thread.query_time = 0.0
        existing = getattr(thread, "query_hooks", None)
        hooks = existing if existing is not None else []
        thread.query_hooks = hooks
        hooks.append(self._record)
        try:
            yield self
        finally:
            hooks.remove(self._record)
            if existing is None and not hooks:
                del thread.query_hooks
            if owns_time:
                del thread.query_count
                del thread.query_time

    def reset(self) -> None:
        self.count = 0
        self._time_start = threading.current_thread().query_time


def measure(
    fn: Callable[[], object], counter: StatementCounter, *, repeat: int, rounds: int = 5
) -> dict[str, float]:
    if repeat < 1 or rounds < 1:
        raise ValueError("repeat and rounds must be positive")
    fn()
    fn()
    samples = []
    statements = []
    for _ in range(rounds):
        counter.reset()
        start = time.perf_counter()
        cpu_start = time.thread_time()
        for _ in range(repeat):
            before = counter.count
            fn()
            statements.append(counter.count - before)
        wall = time.perf_counter() - start
        cpu = time.thread_time() - cpu_start
        samples.append(
            {
                "wall_ms": wall / repeat * 1000,
                "cpu_ms": cpu / repeat * 1000,
                "sql_ms": counter.seconds / repeat * 1000,
                "non_sql_ms": (wall - counter.seconds) / repeat * 1000,
            }
        )
    return {
        **{
            key: round(statistics.median(row[key] for row in samples), 3)
            for key in samples[0]
        },
        "statements": statistics.median(statements),
        "statements_min": min(statements),
        "statements_max": max(statements),
    }


class _Rec:
    __slots__ = ("key", "parent", "value")

    def __init__(self, key: str, value: int, parent: _Rec | None) -> None:
        self.key = key
        self.value = value
        self.parent = parent


def _calibration_workload() -> int:
    index: dict[str, list[_Rec]] = {}
    parent = None
    for i in range(60000):
        rec = _Rec(f"k{i % 997}", i, parent)
        index.setdefault(rec.key, []).append(rec)
        parent = rec if i % 7 else None
    total = 0
    for recs in index.values():
        for rec in recs:
            total += rec.value + (rec.parent.value if rec.parent else 0)
    return total + len(sorted(index, key=lambda key: (len(index[key]), key)))


def calibration_ms(runs: int = 15) -> float:
    # how fast this machine runs interpreter-bound code right now: the fastest
    # of several runs, so a preempted run does not count
    best = float("inf")
    for _ in range(runs):
        start = time.perf_counter()
        _calibration_workload()
        best = min(best, time.perf_counter() - start)
    return round(best * 1000, 3)
