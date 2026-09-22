from __future__ import annotations

import statistics
import time
from collections.abc import Callable
from contextlib import contextmanager


class StatementCounter:
    def __init__(self) -> None:
        self.count = 0
        self.seconds = 0.0

    @contextmanager
    def on(self):
        from odoo.db.cursor import Cursor

        original = Cursor.execute

        def execute(cursor, query, params=None, *args, **kwargs):
            start = time.perf_counter()
            try:
                return original(cursor, query, params, *args, **kwargs)
            finally:
                self.seconds += time.perf_counter() - start
                self.count += 1

        Cursor.execute = execute
        try:
            yield self
        finally:
            Cursor.execute = original

    def reset(self) -> None:
        self.count = 0
        self.seconds = 0.0


def python_ms(
    fn: Callable[[], object], counter: StatementCounter, *, repeat: int, rounds: int = 5
) -> tuple[float, float]:
    """Median over `rounds` of (wall - driver) per call of `fn`, and the statements per call."""
    fn()
    fn()
    samples = []
    statements = []
    for _ in range(rounds):
        counter.reset()
        start = time.perf_counter()
        for _ in range(repeat):
            fn()
        wall = time.perf_counter() - start
        samples.append((wall - counter.seconds) / repeat * 1000)
        statements.append(counter.count / repeat)
    return round(statistics.median(samples), 2), statistics.median(statements)
