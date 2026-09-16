from __future__ import annotations

import logging
import os
import threading
from typing import Any

from odoo.libs.debug_log import DebugLog

from ._env import get_env_float
from .settings import INHERIT_FROM_CRON, current

_debug = DebugLog(__name__)

GRACEFUL_STOP_TIMEOUT_S = 60.0
"""How long a stopping server lets in-flight work finish before it escalates.

One bound for both flavours: the prefork master waits this long for SIGINTed
workers before SIGKILL, and the threaded server waits this long for its busy
request threads before closing the listener under them.
"""


def get_graceful_stop_timeout(logger: logging.Logger) -> float:
    return get_env_float(
        "ODOO_GRACEFUL_STOP_TIMEOUT",
        GRACEFUL_STOP_TIMEOUT_S,
        minimum=1.0,
        logger=logger,
    )


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


def describe_thread_work(thread: threading.Thread) -> str:
    # What the operator will want beside the thread name or pid: the request
    # it is serving (the http layer stamps `url` and `request_id`, the RPC
    # dispatcher `rpc_model_method`) or the database a cron/job pass is
    # sweeping.  The limit verdicts are logged from a monitor thread, so the
    # request id has to travel in the message to join the request's lines.
    kind = getattr(thread, "type", None)
    if kind == "http":
        url = getattr(thread, "url", "")
        if not url:
            return ""
        method = getattr(thread, "rpc_model_method", "")
        text = f"serving {url} ({method})" if method else f"serving {url}"
        if request_id := getattr(thread, "request_id", ""):
            text += f", request {request_id}"
        return text
    db_name = getattr(thread, "dbname", None)
    return f"sweeping {db_name}" if db_name else ""


__all__ = (
    "BACKOFF_BASE_S",
    "BACKOFF_CEILING_S",
    "GRACEFUL_STOP_TIMEOUT_S",
    "INHERIT_FROM_CRON",
    "describe_thread_work",
    "empty_pipe",
    "get_cron_real_time_budget",
    "get_graceful_stop_timeout",
    "get_job_real_time_budget",
    "get_memory_over_soft_limit",
    "get_memory_rss",
)
