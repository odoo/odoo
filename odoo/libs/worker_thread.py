from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING, Protocol, cast

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "WorkerThread",
    "as_worker_thread",
    "current_worker_thread",
    "working_on_database",
]


class WorkerThread(Protocol):
    dbname: str | None
    uid: int | None
    url: str
    request_id: str
    query_count: int
    query_time: float
    perf_t0: float
    cursor_mode: str | None
    rpc_model_method: str
    request_line: str

    type: str

    start_time: float | None

    exec_context: object


def as_worker_thread(thread: threading.Thread) -> WorkerThread:
    return cast("WorkerThread", thread)


def current_worker_thread() -> WorkerThread:
    return as_worker_thread(threading.current_thread())


@contextmanager
def working_on_database(db_name: str) -> Iterator[None]:
    worker = as_worker_thread(threading.current_thread())
    was_set = hasattr(worker, "dbname")
    previous = worker.dbname if was_set else None
    worker.dbname = db_name
    try:
        yield
    finally:
        if was_set:
            worker.dbname = previous
        elif hasattr(worker, "dbname"):
            del worker.dbname
