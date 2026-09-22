from __future__ import annotations

import logging
import threading
import zlib
from collections.abc import Callable
from typing import Any

from odoo.libs.worker_thread import working_on_database
from odoo.modules.registry import Registry

_logger = logging.getLogger(__name__)

STREAM_MODEL = "integration.stream"

_LEASE_KEY = "odoo_stream_leader"


class StreamRuntime:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._leases: dict[str, Any] = {}
        self._held: dict[str, dict[Any, Callable[[], None]]] = {}
        self.identity = ""

    def lease(self, db_name: str, registry: Registry) -> bool:
        with self._lock:
            cursor = self._leases.get(db_name)
            if cursor is not None:
                try:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
                    return True
                except Exception:
                    _logger.warning(
                        "The stream lease of %s was lost; its streams close", db_name
                    )
                    self._drop_lease(db_name)
            cursor = registry.cursor()
            try:
                cursor.execute(
                    "SELECT pg_try_advisory_lock(%s, %s)",
                    [zlib.crc32(_LEASE_KEY.encode()) & 0x7FFFFFFF, _db_key(db_name)],
                )
                taken = bool(cursor.fetchone()[0])
            except Exception:
                cursor.close()
                raise
            if not taken:
                cursor.close()
                return False
            self._leases[db_name] = cursor
            _logger.info("This process leads the streams of %s", db_name)
            return True

    def leads(self, db_name: str) -> bool:
        with self._lock:
            return db_name in self._leases

    def hold(self, db_name: str, key: Any, close: Callable[[], None]) -> None:
        with self._lock:
            self._held.setdefault(db_name, {})[key] = close

    def held(self, db_name: str) -> set[Any]:
        with self._lock:
            return set(self._held.get(db_name, ()))

    def drop(self, db_name: str, key: Any) -> None:
        with self._lock:
            close = self._held.get(db_name, {}).pop(key, None)
        if close is not None:
            _close_quietly(close, db_name, key)

    def release(self, db_name: str) -> None:
        with self._lock:
            held = self._held.pop(db_name, {})
            self._drop_lease(db_name)
        for key, close in held.items():
            _close_quietly(close, db_name, key)

    def shutdown(self) -> None:
        with self._lock:
            databases = list(self._held) + [
                db_name for db_name in self._leases if db_name not in self._held
            ]
        for db_name in databases:
            self.release(db_name)

    def _drop_lease(self, db_name: str) -> None:
        cursor = self._leases.pop(db_name, None)
        if cursor is None:
            return
        try:
            cursor.close()
        except Exception:
            _logger.debug(
                "Could not close the lease cursor of %s", db_name, exc_info=True
            )


def _db_key(db_name: str) -> int:
    return zlib.crc32(db_name.encode()) & 0x7FFFFFFF


def _close_quietly(close: Callable[[], None], db_name: str, key: Any) -> None:
    try:
        close()
    except Exception:
        _logger.warning("Could not close stream %s of %s", key, db_name, exc_info=True)


RUNTIME = StreamRuntime()


def process_streams(db_name: str) -> None:
    """One database's sweep: lead it or leave it, then reconcile."""
    with working_on_database(db_name):
        try:
            registry = Registry(db_name)
        except Exception:
            _logger.warning(
                "Streams of %s: the registry did not load", db_name, exc_info=True
            )
            return
        if STREAM_MODEL not in registry:
            if RUNTIME.leads(db_name):
                RUNTIME.release(db_name)
            return
        if not RUNTIME.lease(db_name, registry):
            return
        registry[STREAM_MODEL]._reconcile(db_name, RUNTIME)


def shutdown() -> None:
    RUNTIME.shutdown()
