from __future__ import annotations

import contextlib
import logging
import threading
from time import monotonic

import psycopg

from odoo.libs.debug_log import DebugLog

from .dsn import (
    _NON_RETRYABLE_CONNECT_ERRORS,
    _expand_conninfo,
    _get_key_dbname,
    _resolve_connect_error,
)

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

PROBE_CONNECT_TIMEOUT = 5


def get_libpq_connect_timeout(deadline: float | None, cap: int) -> int:
    if deadline is None:
        return cap
    remaining = int(deadline - monotonic())
    if remaining < 1:
        return 0
    return min(cap, remaining)


class _InFlightProbe:
    __slots__ = ("connected", "done", "exc")

    def __init__(self) -> None:
        self.done = threading.Event()
        self.exc: BaseException | None = None
        self.connected = True


class ReachabilityProbe:
    def __init__(self, stats) -> None:
        self._lock = threading.Lock()
        self._proven: set[frozenset] = set()
        self._inflight: dict[frozenset, _InFlightProbe] = {}
        self._stats = stats

    def is_proven(self, key: frozenset) -> bool:
        with self._lock:
            return key in self._proven

    def mark_proven(self, key: frozenset) -> None:
        # Lock-free first look: set membership is one atomic read, and this runs
        # on every borrow (157 ns with the lock, 27 ns without); a stale miss
        # only takes the lock it would have taken anyway.
        if key in self._proven:
            return
        with self._lock:
            if _debug.lifecycle.enabled and key not in self._proven:
                _debug.lifecycle(
                    "pool.reachability_proven",
                    db=_get_key_dbname(key),
                    proven=len(self._proven) + 1,
                )
            self._proven.add(key)

    def clear_key(self, key: frozenset) -> None:
        with self._lock:
            if _debug.lifecycle.enabled and key in self._proven:
                _debug.lifecycle("pool.reachability_revoked", db=_get_key_dbname(key))
            self._proven.discard(key)

    def clear_keys(self, keys) -> None:
        with self._lock:
            _debug.lifecycle("pool.reachability_revoked", count=len(keys))
            self._proven.difference_update(keys)

    def clear(self) -> None:
        with self._lock:
            _debug.lifecycle("pool.reachability_revoked", count=len(self._proven))
            self._proven.clear()

    def clear_database(self, db_name: str) -> None:
        with self._lock:
            revoked = [key for key in self._proven if _get_key_dbname(key) == db_name]
            _debug.lifecycle(
                "pool.reachability_revoked", db=db_name, count=len(revoked)
            )
            self._proven.difference_update(revoked)

    def check_connectable(
        self,
        key: frozenset,
        conninfo: str,
        kwargs: dict,
        deadline: float | None = None,
    ) -> bool:
        with self._lock:
            if key in self._proven:
                proven = True
                probe = None
                leader = False
            else:
                proven = False
                probe = self._inflight.get(key)
                leader = probe is None
                if leader:
                    probe = self._inflight[key] = _InFlightProbe()
        if proven:
            self._stats.record_probe_outcome("skipped_proven")
            _debug.logic("pool.probe.skipped_proven", db=_get_key_dbname(key))
            return True
        assert probe is not None
        _debug.logic(
            "pool.probe",
            db=_get_key_dbname(key),
            leader=leader,
            deadline_s=None if deadline is None else max(0.0, deadline - monotonic()),
        )
        return self._probe_or_await_leader(
            key, probe, leader, conninfo, kwargs, deadline
        )

    # True unless a connect was attempted and failed transiently; a permanent
    # failure raises. A follower that gave up waiting answers True: it knows
    # nothing, and the borrow's own deadline decides.
    def _probe_or_await_leader(
        self,
        key: frozenset,
        probe: _InFlightProbe,
        leader: bool,
        conninfo: str,
        kwargs: dict,
        deadline: float | None = None,
    ) -> bool:
        if leader:
            try:
                probe.connected = (
                    self.probe_connectable(conninfo, kwargs, deadline) is not False
                )
            except BaseException as e:
                probe.exc = e
                raise
            finally:
                with self._lock:
                    del self._inflight[key]
                    probe.done.set()
                _debug.pipeline(
                    "pool.probe.leader_done",
                    db=_get_key_dbname(key),
                    failed=probe.exc is not None,
                    connected=probe.connected,
                )
            return probe.connected
        else:
            wait_timeout = (
                None if deadline is None else max(0.0, deadline - monotonic())
            )
            done = probe.done.wait(wait_timeout)
            _debug.logic(
                "pool.probe.awaited",
                db=_get_key_dbname(key),
                done=done,
                failed=probe.exc is not None,
            )
            if done and probe.exc is not None:
                raise probe.exc.with_traceback(None)
            return probe.connected if done else True

    def probe_connectable(
        self, conninfo: str, kwargs: dict, deadline: float | None = None
    ) -> bool:
        probe_timeout = get_libpq_connect_timeout(deadline, PROBE_CONNECT_TIMEOUT)
        if not probe_timeout:
            _debug.logic("pool.probe.skipped_deadline", db=kwargs.get("dbname"))
            return True
        self._stats.record_probe_started()
        probe_kwargs = {**kwargs, "autocommit": True}
        probe_kwargs["connect_timeout"] = probe_timeout
        try:
            with _debug.perf("pool.probe.connect", timeout=probe_timeout):
                conn = psycopg.connect(conninfo, **probe_kwargs)
        except _NON_RETRYABLE_CONNECT_ERRORS as e:
            self._stats.record_probe_outcome("permanent")
            _debug.logic(
                "pool.probe.permanent", reason="sqlstate", error=type(e).__name__
            )
            raise
        except psycopg.OperationalError as e:
            translated = _resolve_connect_error(e)
            if translated is not None:
                self._stats.record_probe_outcome("permanent")
                _debug.logic(
                    "pool.probe.permanent",
                    reason="message",
                    error=type(translated).__name__,
                )
                raise translated from e
            if self.is_database_absent(conninfo, kwargs, deadline):
                self._stats.record_probe_outcome("permanent")
                _debug.logic("pool.probe.permanent", reason="database_absent")
                raise psycopg.errors.InvalidCatalogName(str(e)) from e
            self._stats.record_probe_outcome("transient")
            _debug.logic("pool.probe.transient", error=type(e).__name__)
            _logger.debug(
                "Pool pre-flight probe failed (treating as transient)",
                exc_info=True,
            )
            return False
        except Exception as e:
            self._stats.record_probe_outcome("transient")
            _debug.logic("pool.probe.transient", error=type(e).__name__)
            _logger.debug(
                "Pool pre-flight probe failed (treating as transient)",
                exc_info=True,
            )
            return False
        _debug.lifecycle(
            "pool.probe.ok",
            db=kwargs.get("dbname"),
            backend_pid=getattr(getattr(conn, "info", None), "backend_pid", None),
        )
        with contextlib.suppress(Exception):
            conn.close()
        return True

    def is_database_absent(
        self, conninfo: str, kwargs: dict, deadline: float | None = None
    ) -> bool:
        maint = _expand_conninfo({"dsn": conninfo, **kwargs})
        db_name = maint.get("dbname")
        if not db_name or db_name == "postgres":
            _debug.logic(
                "pool.probe.absence_check_skipped",
                db=db_name,
                reason="maintenance_db" if db_name else "no_db_name",
            )
            return False
        maint.pop("options", None)
        maint["dbname"] = "postgres"
        maint["autocommit"] = True
        probe_timeout = get_libpq_connect_timeout(deadline, PROBE_CONNECT_TIMEOUT)
        if not probe_timeout:
            _debug.logic(
                "pool.probe.absence_check_skipped", db=db_name, reason="deadline"
            )
            return False
        maint["connect_timeout"] = probe_timeout
        try:
            with psycopg.connect("", **maint) as mc:
                row = mc.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)
                ).fetchone()
            _debug.logic("pool.probe.database_absent", db=db_name, absent=row is None)
            return row is None
        except Exception as e:
            _debug.logic(
                "pool.probe.absence_check_unavailable",
                db=db_name,
                error=type(e).__name__,
            )
            _logger.debug(
                "pg_database existence check unavailable for %r",
                db_name,
                exc_info=True,
            )
            return False
