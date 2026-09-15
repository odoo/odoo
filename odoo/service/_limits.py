from __future__ import annotations

import os
from typing import Any

from odoo.libs.debug_log import DebugLog

from .settings import INHERIT_FROM_CRON, current

_debug = DebugLog(__name__)

BACKOFF_CEILING_S = 60
"""Longest a reconnect back-off will wait.

Its own constant.  It was `SLEEP_INTERVAL`, the cron poll interval, which three
unrelated things had borrowed for the number 60 rather than the meaning: this
ceiling, the cron sweep cadence, and how long `ThreadedServer.run` lets
in-flight requests finish before reloading.  Tuning any one of them moved the
other two.
"""

BACKOFF_BASE_S = 2
"""What a reconnect waits after its first failure, doubling from there.

Stated rather than implied.  The curve came from a second exponential
backoff in this package -- `min(2 ** attempts, ceiling)` over a 0-based
counter, so the base was the offset and neither was written down.
`odoo.libs.backoff` is the one implementation now, 1-based with an explicit
base, and `base=2` is what reproduces this curve exactly.
"""


def get_cron_real_time_budget() -> float:
    return current().cron_real_time_budget


def get_job_real_time_budget() -> float:
    return current().job_real_time_budget


def get_memory_rss(process: Any) -> int:
    return process.memory_info().rss


def get_memory_over_soft_limit(process: Any, soft_limit: int) -> int | None:
    if not soft_limit:
        return None
    memory = get_memory_rss(process)
    _debug.perf.count(
        "limits.memory_sampled",
        rss=memory,
        soft_limit=soft_limit,
        over=memory > soft_limit,
    )
    return memory if memory > soft_limit else None


def empty_pipe(fd: int) -> None:
    try:
        while os.read(fd, 4096):
            pass
    except BlockingIOError:
        pass


__all__ = (
    "BACKOFF_BASE_S",
    "BACKOFF_CEILING_S",
    "INHERIT_FROM_CRON",
    "empty_pipe",
    "get_cron_real_time_budget",
    "get_job_real_time_budget",
    "get_memory_over_soft_limit",
    "get_memory_rss",
)
