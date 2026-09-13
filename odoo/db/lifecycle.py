from __future__ import annotations

from time import monotonic

import psycopg
from psycopg.adapt import Loader
from psycopg_pool import ConnectionPool as _PsycopgPool

from odoo.libs.debug_log import DebugLog

from .settings import current

_debug = DebugLog(__name__)

_PREPARE_THRESHOLD = 2
"""Executions of one statement text before psycopg prepares it server-side.

Worth knowing when writing a probe: a prepared statement runs through a NAMED
portal, so a query that reads a catalog view describing the session's own
execution state starts counting itself at its third execution. Measured,
`SELECT count(*) FROM pg_cursors` on one connection answers 0, 0, 1, 1, 1
against a `pg_cursors` that is empty throughout. Nothing in the tree reads
those views, so this bites diagnostics rather than production -- but it looks
exactly like a session-state leak, and `TestResetConnectionClosesSessionGucLeak`
filters by cursor name rather than counting for that reason.
"""
_PREPARED_MAX = 500

_IDLE_SINCE_ATTR = "_odoo_idle_since"

_RESET_SESSION_STATE_SQL = (
    "RESET ALL;"
    " RESET SESSION AUTHORIZATION;"
    " CLOSE ALL;"
    " UNLISTEN *;"
    " SELECT pg_advisory_unlock_all();"
    " DISCARD TEMP;"
    " DISCARD SEQUENCES"
)


def clear_prepared_cache(conn: psycopg.Connection) -> bool:
    prepared = getattr(conn, "_prepared", None)
    if prepared is None:
        _debug.logic("connection.prepared_cache_unavailable", reason="no_attribute")
        return False
    try:
        prepared.clear()
    except Exception as e:
        _debug.logic(
            "connection.prepared_cache_unavailable",
            reason="clear_failed",
            error=type(e).__name__,
        )
        return False
    _debug.lifecycle("connection.prepared_cache_cleared")
    return True


class _NumericToFloatLoader(Loader):
    def load(self, data: bytes) -> float:
        return float(data)


def register_adapters(conn: psycopg.Connection) -> None:
    conn.adapters.register_loader("numeric", _NumericToFloatLoader)


def _mark_idle(conn: psycopg.Connection) -> None:
    conn.prepare_threshold = _PREPARE_THRESHOLD
    conn.prepared_max = _PREPARED_MAX
    setattr(conn, _IDLE_SINCE_ATTR, monotonic())


def _configure_connection(conn: psycopg.Connection) -> None:
    register_adapters(conn)
    _mark_idle(conn)
    _debug.lifecycle(
        "connection.configured",
        backend_pid=getattr(getattr(conn, "info", None), "backend_pid", None),
        prepare_threshold=_PREPARE_THRESHOLD,
        prepared_max=_PREPARED_MAX,
    )


def _reset_connection(conn: psycopg.Connection, *, discard: bool | None = None) -> None:
    if discard is None:
        discard = current().discard_on_return
    with _debug.perf("connection.reset", discard=discard):
        if discard:
            conn.autocommit = True
            conn.execute("DISCARD ALL", prepare=False)
            clear_prepared_cache(conn)
        else:
            conn.autocommit = True
            conn.execute(_RESET_SESSION_STATE_SQL, prepare=False)
    conn.autocommit = False
    conn.isolation_level = None
    conn.read_only = None
    _mark_idle(conn)
    _debug.lifecycle(
        "connection.returned_idle",
        discard=discard,
        backend_pid=getattr(getattr(conn, "info", None), "backend_pid", None),
    )


def _check_connection(conn: psycopg.Connection, *, grace: float | None = None) -> None:
    if grace is None:
        grace = current().healthcheck_grace
    idle_since = getattr(conn, _IDLE_SINCE_ATTR, None)
    if grace and idle_since is not None and monotonic() - idle_since < grace:
        _debug.logic(
            "connection.healthcheck_skipped",
            idle_s=monotonic() - idle_since,
            grace=grace,
        )
        return
    with _debug.perf(
        "connection.healthcheck",
        idle_s=None if idle_since is None else monotonic() - idle_since,
    ):
        _PsycopgPool.check_connection(conn)
