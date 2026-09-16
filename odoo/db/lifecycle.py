from __future__ import annotations

from time import monotonic

import psycopg
from psycopg import IsolationLevel
from psycopg.adapt import Loader
from psycopg.pq import ExecStatus

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

_ISOLATION_LEVEL = IsolationLevel.REPEATABLE_READ

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


def get_backend_pid(conn: object) -> int | None:
    try:
        return getattr(getattr(conn, "info", None), "backend_pid", None)
    except psycopg.OperationalError:
        return None


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


# The two flags psycopg folds into every BEGIN. A pooled connection serves one
# pool for its whole life, so they are set once here and only re-set on return
# when a cursor changed them (enforce_readonly): the pair of setters cost 2.5 us
# per cursor cycle when re-issued unconditionally, the comparison 50 ns.
def _set_transaction_flags(conn: psycopg.Connection, readonly: bool) -> None:
    if conn.isolation_level is not _ISOLATION_LEVEL:
        _debug.logic(
            "connection.flag_set",
            flag="isolation_level",
            was=conn.isolation_level,
            readonly=readonly,
        )
        conn.isolation_level = _ISOLATION_LEVEL
    if conn.read_only is not readonly:
        _debug.logic(
            "connection.flag_set", flag="read_only", was=conn.read_only, now=readonly
        )
        conn.read_only = readonly


def _configure_connection(conn: psycopg.Connection, *, readonly: bool = False) -> None:
    register_adapters(conn)
    _set_transaction_flags(conn, readonly)
    _mark_idle(conn)
    _debug.lifecycle(
        "connection.configured",
        backend_pid=get_backend_pid(conn),
        readonly=readonly,
        prepare_threshold=_PREPARE_THRESHOLD,
        prepared_max=_PREPARED_MAX,
    )


# libpq's simple-query call: one round trip for the multi-statement string, no
# BEGIN folded in (so no autocommit toggle around it) and none of the
# per-statement machinery psycopg's execute() runs -- 14 us against 24 us,
# on a path taken once per cursor cycle.
def _run_simple_query(conn: psycopg.Connection, sql: bytes, expected: int) -> None:
    result = conn.pgconn.exec_(sql)
    if result.status != expected:
        raise psycopg.OperationalError(result.get_error_message())


def _run_session_reset(conn: psycopg.Connection, sql: str) -> None:
    _run_simple_query(conn, sql.encode(), ExecStatus.COMMAND_OK)


# The empty query is what psycopg_pool's own check sends, minus the autocommit
# toggle it wraps around execute(): 8 us against 12.7. A terminated backend
# answers FATAL_ERROR once and raises OperationalError after.
def _probe_liveness(conn: psycopg.Connection) -> None:
    try:
        _run_simple_query(conn, b"", ExecStatus.EMPTY_QUERY)
    except Exception as exc:
        # psycopg_pool discards the connection and says nothing at our level.
        _debug.lifecycle(
            "connection.liveness_failed",
            backend_pid=get_backend_pid(conn),
            error=type(exc).__name__,
        )
        raise


def _reset_connection(
    conn: psycopg.Connection, *, discard: bool | None = None, readonly: bool = False
) -> None:
    if discard is None:
        discard = current().discard_on_return
    with _debug.perf("connection.reset", discard=discard):
        if discard:
            _run_session_reset(conn, "DISCARD ALL")
            clear_prepared_cache(conn)
        else:
            _run_session_reset(conn, _RESET_SESSION_STATE_SQL)
    _set_transaction_flags(conn, readonly)
    _mark_idle(conn)
    _debug.lifecycle(
        "connection.returned_idle",
        discard=discard,
        readonly=readonly,
        backend_pid=get_backend_pid(conn),
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
        _probe_liveness(conn)
