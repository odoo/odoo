from __future__ import annotations

import contextlib
import logging
import os
import re
import sys
import threading
from time import monotonic
from typing import TYPE_CHECKING

import psycopg
from psycopg_pool import ConnectionPool as _PsycopgPool
from psycopg_pool import PoolClosed, PoolTimeout

from odoo.libs.debug_log import DebugLog
from odoo.release import MIN_PG_VERSION

from .budget import ConnectionBudget
from .dsn import _expand_conninfo, _get_dsn_key, _get_key_dbname
from .leaks import CheckoutTracker
from .lifecycle import (
    _check_connection,
    _configure_connection,
    _reset_connection,
    get_backend_pid,
)
from .probe import PROBE_CONNECT_TIMEOUT, ReachabilityProbe, get_libpq_connect_timeout
from .reaper import IdlePoolReaper, mark_active, trim_idle_to_ceiling
from .settings import PoolSettings, resolve
from .stats import PoolStats
from .utils import is_maintenance_db

if TYPE_CHECKING:
    from types import FrameType

_logger = logging.getLogger(__name__)
_logger_conn = _logger.getChild("connection")
_debug = DebugLog(__name__)


class _SuppressKnownPoolWarnings(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "discarding closed connection" in msg:
            return False
        return not ('database "' in msg and "does not exist" in msg)


_psycopg_pool_logger = logging.getLogger("psycopg.pool")
if not any(
    isinstance(f, _SuppressKnownPoolWarnings) for f in _psycopg_pool_logger.filters
):
    _psycopg_pool_logger.addFilter(_SuppressKnownPoolWarnings())

_DIRECT_CONNECTION = object()

_DIRECT_IDLE_SESSION_TIMEOUT_MS = 900 * 1000

_LEAK_REPORT_INTERVAL = 60.0


def _get_seconds_remaining(deadline: float | None) -> float:
    return float("inf") if deadline is None else deadline - monotonic()


def _get_base_connection_options(conninfo: str, kwargs: dict) -> str:
    options = kwargs.get("options", "")
    if not options and conninfo:
        options = _expand_conninfo(conninfo).get("options", "")
    if not options:
        options = os.environ.get("PGOPTIONS", "")
    return options


_GUC_NAME_RE = re.compile(r"-c\s*([A-Za-z_][A-Za-z0-9_.]*)\s*=")
# A comma starts the next entry only when a `name=` follows it, so a list-valued
# GUC (`search_path=public,pg_catalog`) stays one entry.
_GUC_SEPARATOR_RE = re.compile(r",(?=\s*[A-Za-z_][A-Za-z0-9_.]*\s*=)")

_FAKETIME_GUCS: tuple[str, ...] = ("search_path=public,pg_catalog",)


def _prepare_session_gucs(base_options: str, configured: str) -> str:
    already_set = set(_GUC_NAME_RE.findall(base_options))
    gucs = []
    for entry in _GUC_SEPARATOR_RE.split(configured):
        name, _, value = entry.partition("=")
        name, value = name.strip(), value.strip()
        if name and value and name not in already_set:
            gucs.append(f"-c {name}={value}")
    _debug.logic(
        "pool.session_gucs_prepared",
        added=len(gucs),
        already_set=len(already_set),
        configured=configured,
    )
    return " ".join(gucs)


def _prepare_connection_options(
    conninfo: str,
    kwargs: dict,
    idle_session_ms: int,
    *,
    session_gucs: str | None,
    forced_gucs: tuple[str, ...] = (),
    idle_in_transaction_ms: int = 0,
) -> str:
    base = _get_base_connection_options(conninfo, kwargs)
    parts = [
        base,
        _prepare_session_gucs(base, session_gucs) if session_gucs else "",
        f"-c idle_session_timeout={idle_session_ms}",
        f"-c idle_in_transaction_session_timeout={idle_in_transaction_ms}"
        if idle_in_transaction_ms > 0
        else "",
        *(f"-c {guc}" for guc in forced_gucs),
    ]
    return " ".join(p for p in parts if p)


def _get_forced_gucs(dbname: str, settings: PoolSettings) -> tuple[str, ...]:
    if os.getenv("ODOO_FAKETIME_TEST_MODE") and dbname in settings.db_names:
        _debug.logic("pool.search_path_pinned", db=dbname)
        return _FAKETIME_GUCS
    return ()


def _get_borrow_caller() -> str | None:
    frame: FrameType | None = sys._getframe(1)
    while frame is not None:
        name = frame.f_code.co_filename
        if f"{os.sep}odoo{os.sep}db{os.sep}" not in name and not name.endswith(
            f"{os.sep}contextlib.py"
        ):
            return f"{name}:{frame.f_lineno}"
        frame = frame.f_back
    return None


class PoolError(Exception):
    pass


class ConnectionPool:
    def __init__(
        self,
        maxconn: int = 64,
        readonly: bool = False,
        minconn: int | None = None,
        *,
        borrow_timeout: float | None = None,
        max_lifetime: int | None = None,
        max_idle: int | None = None,
        reap_idle_ttl: float | None = None,
        budget: ConnectionBudget | None = None,
        pool_workers: int | None = None,
        settings: PoolSettings | None = None,
    ):
        settings = resolve(settings)
        if minconn is None:
            minconn = settings.minconn
        if borrow_timeout is None:
            borrow_timeout = settings.borrow_timeout
        if max_lifetime is None:
            max_lifetime = settings.conn_max_lifetime
        if max_idle is None:
            max_idle = settings.conn_max_idle
        if reap_idle_ttl is None:
            reap_idle_ttl = settings.pool_reap_idle
        if pool_workers is None:
            pool_workers = settings.pool_workers
        if maxconn <= 0:
            raise ValueError(f"ConnectionPool maxconn must be >= 1, got {maxconn}")
        if minconn < 0:
            raise ValueError(f"ConnectionPool minconn must be >= 0, got {minconn}")
        if pool_workers < 1:
            raise ValueError(
                f"ConnectionPool pool_workers must be >= 1, got {pool_workers}"
            )
        if minconn > maxconn:
            raise ValueError(
                f"ConnectionPool minconn ({minconn}) cannot exceed maxconn ({maxconn})"
            )
        self._pools: dict[frozenset, _PsycopgPool] = {}
        self._maxconn = maxconn
        self._minconn = minconn
        self._readonly = readonly
        self._borrow_timeout = borrow_timeout
        self._max_lifetime = max_lifetime
        self._max_idle = max_idle
        self._pool_workers = pool_workers
        self._settings = settings
        self._reaper = IdlePoolReaper(reap_idle_ttl)
        self._lock = threading.Lock()
        self.stats = PoolStats()
        self._checkouts = CheckoutTracker()
        self._budget = budget if budget is not None else ConnectionBudget(maxconn)
        self._direct_out = 0
        self._probe = ReachabilityProbe(self.stats)
        _debug.lifecycle(
            "pool.manager_created",
            readonly=readonly,
            maxconn=maxconn,
            minconn=minconn,
            borrow_timeout=borrow_timeout,
            max_lifetime=max_lifetime,
            max_idle=max_idle,
            reap_idle_ttl=reap_idle_ttl,
            own_budget=budget is None,
            workers=pool_workers,
        )

    def __repr__(self) -> str:
        pools = list(self._pools.values())
        total = available = 0
        for p in pools:
            stats = p.get_stats()
            total += stats.get("pool_size", 0)
            available += stats.get("pool_available", 0)
        used = total - available
        mode = "read-only" if self._readonly else "read/write"
        direct = self._direct_out
        return (
            f"ConnectionPool({mode};used={used}/total={total}"
            f"/limit={self._budget.maxconn};dbs={len(pools)};direct={direct})"
        )

    @property
    def readonly(self) -> bool:
        return self._readonly

    def _log_connection(self, msg: str, *args: object) -> None:
        _logger_conn.debug(("%r " + msg), self, *args)

    def _get_or_create_pool(
        self,
        key: frozenset,
        connection_info: dict,
        deadline: float | None = None,
        *,
        fail_fast: bool = False,
    ) -> _PsycopgPool:
        pool = self._pools.get(key)
        if pool is not None and not pool.closed:
            if fail_fast and self._is_pool_unproven_and_empty(key, pool):
                # A surviving pool with nothing idle and its proof revoked is
                # psycopg_pool still counting the connections it cannot open:
                # getconn would wait the deadline out. Ask the probe first.
                conninfo, kwargs = self._prepare_connect_args(key, connection_info)
                self._check_connectable_or_fail_fast(
                    key, conninfo, kwargs, deadline, fail_fast=True
                )
            mark_active(pool)
            return pool

        conninfo, kwargs = self._prepare_connect_args(key, connection_info)
        self._check_connectable_or_fail_fast(
            key, conninfo, kwargs, deadline, fail_fast=fail_fast
        )

        with self._lock:
            pool = self._pools.get(key)
            if pool is not None and not pool.closed:
                _debug.logic("pool.create_raced", db=_get_key_dbname(key), won=False)
                mark_active(pool)
                return pool

            with _debug.perf(
                "pool.open",
                db=_get_key_dbname(key),
                readonly=self._readonly,
                min=self._minconn,
                idle_session_ms=self._get_idle_session_ms(),
                rebuilt=pool is not None,
            ):
                pool = _PsycopgPool(
                    conninfo,
                    connection_class=psycopg.Connection,
                    kwargs=kwargs,
                    min_size=self._minconn,
                    max_size=self._maxconn,
                    max_lifetime=self._max_lifetime,
                    max_idle=self._max_idle,
                    reconnect_timeout=15,
                    configure=self._configure_connection,
                    reset=None,
                    check=self._check_connection,
                    num_workers=self._pool_workers,
                    open=True,
                )
            mark_active(pool)
            self._pools[key] = pool
            self.stats.record_pool_created()
            self._log_connection("Created pool for %s", dict(key))
            _debug.lifecycle(
                "pool.created",
                db=_get_key_dbname(key),
                readonly=self._readonly,
                pools=len(self._pools),
                min=self._minconn,
                max=self._maxconn,
            )

            ident = frozenset(t for t in key if t[0] != "password_fp")
            stale_keys = [
                k
                for k in self._pools
                if k != key
                and frozenset(t for t in k if t[0] != "password_fp") == ident
            ]
            stale_pools = [self._pools.pop(k) for k in stale_keys]
            self._probe.clear_keys(stale_keys)

            reap_keys = self._reaper.get_keys_reapable(self._pools, exclude_key=key)
            reaped_pools = [self._pools.pop(k) for k in reap_keys]

        for sp in stale_pools:
            self._close_pool_safely(sp)
        if stale_pools:
            self.stats.record_pools_evicted_stale(len(stale_pools))
            _debug.lifecycle("pool.stale_credential_evicted", count=len(stale_pools))
            _logger.info(
                "%r: evicted %d stale-credential pool(s) after key change",
                self,
                len(stale_pools),
            )
        for rp in reaped_pools:
            self._close_pool_safely(rp)
        if reaped_pools:
            self.stats.record_pools_reaped(len(reaped_pools))
            _debug.lifecycle("pool.reaped", trigger="create", count=len(reaped_pools))
            _logger.info(
                "%r: reaped %d idle pool(s) (>%.0fs since last borrow)",
                self,
                len(reaped_pools),
                self._reaper.ttl,
            )
        return pool

    def _get_idle_session_ms(self) -> int:
        return max(900, int(self._max_idle * 1.5)) * 1000

    def _prepare_connect_args(
        self, key: frozenset, connection_info: dict
    ) -> tuple[str, dict]:
        kwargs = dict(connection_info)
        conninfo = kwargs.pop("dsn", "")
        kwargs["autocommit"] = False
        kwargs["options"] = _prepare_connection_options(
            conninfo,
            kwargs,
            self._get_idle_session_ms(),
            session_gucs=self._settings.session_gucs,
            forced_gucs=_get_forced_gucs(_get_key_dbname(key), self._settings),
            idle_in_transaction_ms=int(
                self._settings.idle_in_transaction_timeout * 1000
            ),
        )
        return conninfo, kwargs

    def _check_connectable_or_fail_fast(
        self,
        key: frozenset,
        conninfo: str,
        kwargs: dict,
        deadline: float | None,
        *,
        fail_fast: bool,
    ) -> None:
        if self._probe.check_connectable(key, conninfo, kwargs, deadline):
            return
        if fail_fast:
            dbname = _get_key_dbname(key)
            _debug.logic("pool.borrow_refused", db=dbname, reason="fail_fast")
            raise PoolError(
                f"Could not connect to {dbname!r} and the caller asked not to "
                f"wait for it (fail_fast)"
            )

    def _is_pool_unproven_and_empty(self, key: frozenset, pool: _PsycopgPool) -> bool:
        if self._probe.is_proven(key):
            return False
        return pool.get_stats().get("pool_available", 0) == 0

    def _reap_idle_pools_if_due(self) -> None:
        if not self._reaper.is_probably_due():
            return
        with self._lock:
            if not self._reaper.acquire_check_interval():
                _debug.logic("pool.reap_skipped", reason="interval_taken")
                return
            reap_keys = self._reaper.get_keys_reapable(self._pools)
            reaped_pools = [self._pools.pop(k) for k in reap_keys]
        _debug.pipeline(
            "pool.reap_sweep",
            readonly=self._readonly,
            reaped=len(reaped_pools),
            ttl=self._reaper.ttl,
        )
        if reaped_pools:
            IdlePoolReaper.close_pools_in_background(
                self._close_reaped_pools, reaped_pools, "odoo.db.pool-reaper"
            )

    def _close_reaped_pools(self, pools: list[_PsycopgPool]) -> None:
        for rp in pools:
            self._close_pool_safely(rp)
        self.stats.record_pools_reaped(len(pools))
        _debug.lifecycle(
            "pool.reaped", trigger="return", count=len(pools), ttl=self._reaper.ttl
        )
        _logger.info(
            "%r: reaped %d idle pool(s) on return (>%.0fs since last borrow)",
            self,
            len(pools),
            self._reaper.ttl,
        )

    def borrow(
        self,
        connection_info: dict,
        key: frozenset | None = None,
        *,
        timeout: float | None = None,
        fail_fast: bool = False,
    ) -> psycopg.Connection:
        started = monotonic()
        deadline = started + (self._borrow_timeout if timeout is None else timeout)
        if key is None:
            key = _get_dsn_key(connection_info)
        dbname = _get_key_dbname(key)
        if is_maintenance_db(dbname, self._settings):
            _debug.logic("pool.borrow_routed", db=dbname, route="direct")
            return self._borrow_directly(connection_info, deadline)
        try:
            pool = self._get_or_create_pool(
                key, connection_info, deadline, fail_fast=fail_fast
            )
        except BaseException as exc:
            self.stats.record_borrow_failed()
            _debug.logic(
                "pool.borrow_failed",
                db=dbname,
                stage="pool",
                error=type(exc).__name__,
                waited_ms=(monotonic() - started) * 1000.0,
            )
            raise

        if not self._budget.acquire(deadline - monotonic()):
            self.stats.record_borrow_failed()
            _debug.logic(
                "pool.budget_exhausted",
                db=dbname,
                budget=self._budget.maxconn,
                pools=len(self._pools),
                direct=self._direct_out,
                waited_ms=(monotonic() - started) * 1000.0,
            )
            raise self._prepare_budget_exhausted_error()
        conn = None
        try:
            conn, pool = self._get_connection_with_retry(
                pool, key, connection_info, deadline
            )
            self._check_borrowed_connection(conn, pool)
            self._probe.mark_proven(key)
            self._checkouts.track(conn, _get_borrow_caller())
            self._warn_about_leaks()
            self.stats.record_borrow(started)
            if _debug.perf.enabled:
                pool_stats = pool.get_stats()  # debuglog
                _debug.perf.count(
                    "pool.borrow",
                    db=dbname,
                    wait_ms=(monotonic() - started) * 1000.0,
                    pool_size=pool_stats.get("pool_size", 0),
                    available=pool_stats.get("pool_available", 0),
                    waiting=pool_stats.get("requests_waiting", 0),
                    checked_out=len(self._checkouts),
                    backend_pid=get_backend_pid(conn),
                    thread=threading.current_thread().name,
                )
            return conn
        except BaseException as exc:
            self.stats.record_borrow_failed()
            _debug.logic(
                "pool.borrow_failed",
                db=dbname,
                stage="connection",
                error=type(exc).__name__,
                marked=conn is not None and "_odoo_pool" in conn.__dict__,
                waited_ms=(monotonic() - started) * 1000.0,
            )
            self._unwind_failed_borrow(conn)
            raise

    def _prepare_budget_exhausted_error(self) -> PoolError:
        with self._lock:
            pools, direct_out = len(self._pools), self._direct_out
        return PoolError(
            f"Could not acquire connection: connection budget "
            f"({self._budget.maxconn}) reached, "
            f"all connections are in use across {pools} database(s) "
            f"(+{direct_out} direct maintenance connection(s)). "
            f"{self._checkouts.describe()}"
        )

    def _unwind_failed_borrow(self, conn: psycopg.Connection | None) -> None:
        _debug.lifecycle(
            "pool.borrow_unwound",
            marked=conn is not None and "_odoo_pool" in conn.__dict__,
            closed=None if conn is None else getattr(conn, "closed", None),
        )
        if conn is not None and "_odoo_pool" in conn.__dict__:
            self.give_back(conn, keep_in_pool=False)
        else:
            self._budget.release()

    @property
    def settings(self) -> PoolSettings:
        return self._settings

    def _configure_connection(self, conn: psycopg.Connection) -> None:
        _configure_connection(conn, readonly=self._readonly)

    def _reset_connection(self, conn: psycopg.Connection) -> None:
        _reset_connection(
            conn, discard=self._settings.discard_on_return, readonly=self._readonly
        )

    def _check_connection(self, conn: psycopg.Connection) -> None:
        _check_connection(conn, grace=self._settings.healthcheck_grace)

    def _warn_about_leaks(self) -> None:
        threshold = self._settings.leak_detection
        if not threshold:
            return
        if not self._checkouts.acquire_report_interval(
            max(_LEAK_REPORT_INTERVAL, threshold)
        ):
            return
        held = self._checkouts.describe(older_than=threshold)
        if held:
            self.stats.record_leak_report()
            _debug.lifecycle(
                "pool.leak_reported",
                threshold=threshold,
                outstanding=len(self._checkouts),
                oldest_s=self._checkouts.get_oldest_age(),
            )
            _logger.warning(
                "%r: connection(s) checked out longer than %ss; %s",
                self,
                threshold,
                held,
            )

    def _borrow_directly(
        self, connection_info: dict, deadline: float | None = None
    ) -> psycopg.Connection:
        kwargs = dict(connection_info)
        conninfo = kwargs.pop("dsn", "")
        kwargs["autocommit"] = False
        kwargs["options"] = _prepare_connection_options(
            conninfo, kwargs, _DIRECT_IDLE_SESSION_TIMEOUT_MS, session_gucs=None
        )
        if not self._budget.acquire(_get_seconds_remaining(deadline)):
            self.stats.record_borrow_failed()
            _debug.logic(
                "pool.budget_exhausted",
                db=kwargs.get("dbname"),
                stage="direct",
                budget=self._budget.maxconn,
                direct=self._direct_out,
            )
            raise self._prepare_budget_exhausted_error()
        conn = None
        try:
            if deadline is not None:
                connect_timeout = get_libpq_connect_timeout(
                    deadline, int(kwargs.get("connect_timeout", PROBE_CONNECT_TIMEOUT))
                )
                if not connect_timeout:
                    _debug.logic(
                        "pool.direct_deadline_passed",
                        db=kwargs.get("dbname"),
                        borrow_timeout=self._borrow_timeout,
                    )
                    raise PoolError(
                        f"Could not acquire connection to maintenance database "
                        f"within the {self._borrow_timeout}s borrow budget"
                    )
                kwargs["connect_timeout"] = connect_timeout
            with _debug.perf(
                "pool.direct_connect",
                db=kwargs.get("dbname"),
                connect_timeout=kwargs.get("connect_timeout"),
            ):
                conn = psycopg.connect(conninfo, **kwargs)
            try:
                self._configure_connection(conn)
                self._check_min_server_version(conn)
            except BaseException:
                with contextlib.suppress(Exception):
                    conn.close()
                conn = None
                raise
            conn._odoo_pool = _DIRECT_CONNECTION
            with self._lock:
                self._direct_out += 1
            self._checkouts.track(conn, _get_borrow_caller())
            self.stats.record_direct_borrow()
            _debug.lifecycle(
                "pool.borrow_direct",
                db=kwargs.get("dbname"),
                direct_out=self._direct_out,
            )
            return conn
        except BaseException as exc:
            self.stats.record_borrow_failed()
            _debug.logic(
                "pool.borrow_failed",
                db=kwargs.get("dbname"),
                stage="direct",
                error=type(exc).__name__,
                marked=conn is not None,
            )
            self._unwind_failed_borrow(conn)
            raise

    @staticmethod
    def _check_min_server_version(conn: psycopg.Connection) -> None:
        sv = conn.info.server_version
        if sv < MIN_PG_VERSION * 10000:
            _debug.logic("pool.server_version_refused", server_version=sv)
            raise PoolError(
                f"PostgreSQL {sv // 10000}.{sv % 10000} is below the "
                f"minimum required {MIN_PG_VERSION}.0. Please upgrade "
                f"to PostgreSQL {MIN_PG_VERSION} or later."
            )

    def _get_connection_with_retry(
        self,
        pool: _PsycopgPool,
        key: frozenset,
        connection_info: dict,
        deadline: float,
    ) -> tuple[psycopg.Connection, _PsycopgPool]:
        rebuilt = False
        while True:
            remaining = max(0.1, deadline - monotonic())
            try:
                return pool.getconn(timeout=remaining), pool
            except PoolClosed as e:
                self._discard_pool(key, pool)
                if rebuilt:
                    _logger.info("Connection to the database failed: %s", e)
                    raise PoolError(str(e)) from e
                self._log_connection(
                    "Pool closed under borrow(); rebuilding for %s", dict(key)
                )
                _debug.lifecycle("pool.rebuilt_under_borrow", db=_get_key_dbname(key))
                pool = self._get_or_create_pool(key, connection_info, deadline)
                rebuilt = True
            except PoolTimeout as e:
                _debug.logic(
                    "pool.borrow_timeout",
                    db=_get_key_dbname(key),
                    rebuilt=rebuilt,
                    pool_size=pool.get_stats().get("pool_size", 0),
                    waiting=pool.get_stats().get("requests_waiting", 0),
                )
                if pool.get_stats().get("pool_size", 0) == 0:
                    self._discard_pool(key, pool)
                    _debug.lifecycle(
                        "pool.closed_after_timeout", db=_get_key_dbname(key)
                    )
                self._probe.clear_key(key)
                _logger.info("Connection to the database failed: %s", e)
                raise PoolError(str(e)) from e
            except psycopg.Error as e:
                self._probe.clear_key(key)
                _debug.logic(
                    "pool.getconn_failed",
                    db=_get_key_dbname(key),
                    rebuilt=rebuilt,
                    error=type(e).__name__,
                    sqlstate=getattr(e, "sqlstate", None),
                )
                _logger.info("Connection to the database failed: %s", e)
                raise

    def _discard_pool(self, key: frozenset, pool: _PsycopgPool) -> None:
        with self._lock:
            if self._pools.get(key) is pool:
                del self._pools[key]
        self._close_pool_safely(pool)

    def _check_borrowed_connection(
        self, conn: psycopg.Connection, pool: _PsycopgPool
    ) -> None:
        try:
            self._check_min_server_version(conn)
            if _logger_conn.isEnabledFor(logging.DEBUG):
                self._log_connection(
                    "Borrow connection backend PID %d", conn.info.backend_pid
                )
            conn._odoo_pool = pool
        except BaseException as exc:
            _debug.logic(
                "pool.borrowed_connection_rejected",
                error=type(exc).__name__,
                closed=getattr(conn, "closed", None),
            )
            with contextlib.suppress(Exception):
                pool.putconn(conn)
            raise

    def give_back(
        self, connection: psycopg.Connection, keep_in_pool: bool = True
    ) -> None:
        if _logger_conn.isEnabledFor(logging.DEBUG):
            if not connection.closed:
                self._log_connection("Give back connection to %r", connection.info.dsn)
            else:
                self._log_connection("Give back dead connection %r", connection)
        held_s = self._checkouts.release(connection)
        pool = connection.__dict__.pop("_odoo_pool", None)
        if pool is None:
            _debug.logic("pool.give_back_unmarked", closed=connection.closed)
            if not connection.closed:
                connection.close()
            return
        if pool is _DIRECT_CONNECTION:
            with contextlib.suppress(Exception):
                connection.close()
            with self._lock:
                self._direct_out -= 1
            self._budget.release()
            _debug.pipeline(
                "pool.give_back",
                route="direct",
                held_s=held_s,
                direct_out=self._direct_out,
            )
            self._reap_idle_pools_safely()
            return

        _debug.pipeline(
            "pool.give_back",
            route="pooled",
            held_s=held_s,
            keep_in_pool=keep_in_pool,
            closed=connection.closed,
            outstanding=len(self._checkouts),
        )
        mark_active(pool)
        try:
            if keep_in_pool:
                keep_in_pool = self._reset_returned_connection(connection)
            if not keep_in_pool:
                self.stats.record_connection_discarded()
                _debug.lifecycle(
                    "pool.connection_discarded",
                    closed=connection.closed,
                    pool_size=pool.get_stats().get("pool_size", 0),
                )
                with contextlib.suppress(Exception):
                    connection.close()

            try:
                pool.putconn(connection)
            except Exception as exc:
                _debug.logic("pool.putconn_failed", error=type(exc).__name__)
                _logger.debug("Failed to return connection to pool", exc_info=True)
        finally:
            self._budget.release()
        if len(self._pools) > 1:
            self._trim_to_ceiling_safely()
        self._reap_idle_pools_safely()

    def _trim_to_ceiling_safely(self) -> None:
        try:
            with self._lock:
                pools = dict(self._pools)
            trimmed = trim_idle_to_ceiling(pools, self._maxconn)
        except Exception as exc:
            _debug.logic("pool.trim_failed", error=type(exc).__name__)
            _logger.debug("Backend-ceiling trim on give_back failed", exc_info=True)
            return
        if trimmed:
            self.stats.record_connections_trimmed(trimmed)

    # The session reset runs here, on the returning thread, not in psycopg_pool's
    # worker: with `reset=` set, putconn hands every return to the pool's one
    # worker, the next getconn finds nothing idle and grows the pool instead of
    # waiting -- measured, 8 request threads held 63 backends -- and every
    # return for a database queues behind that one thread. Reset first, and
    # putconn files an idle connection synchronously.
    def _reset_returned_connection(self, connection: psycopg.Connection) -> bool:
        try:
            self._reset_connection(connection)
        except Exception as exc:
            _debug.logic("pool.reset_on_return_failed", error=type(exc).__name__)
            _logger.debug("Session reset on return failed", exc_info=True)
            return False
        return True

    def _reap_idle_pools_safely(self) -> None:
        try:
            self._reap_idle_pools_if_due()
        except Exception as exc:
            _debug.logic("pool.reap_failed", error=type(exc).__name__)
            _logger.debug("Idle-pool reap on give_back failed", exc_info=True)

    @staticmethod
    def _close_pool_safely(pool: _PsycopgPool) -> None:
        try:
            pool.close()
        except Exception as exc:
            _debug.logic("pool.close_failed", error=type(exc).__name__)
            _logger.debug("Failed to close pool during teardown", exc_info=True)

    @staticmethod
    def _drain_pool_safely(pool: _PsycopgPool) -> None:
        try:
            pool.drain()
        except Exception as exc:
            _debug.logic("pool.drain_failed", error=type(exc).__name__)
            _logger.debug("Failed to drain pool", exc_info=True)

    # libpq's PQcancel from the client side: no borrow (a saturated pool is
    # when this is needed), no pg_signal_backend privilege, and it reaches a
    # replica connection too. A cancel that fails is a connection that is
    # already gone or a backend that already finished; either way nothing to do.
    _CANCEL_TIMEOUT = 2.0

    def cancel_queries_of(self, thread_name: str) -> int:
        cancelled = 0
        for conn in self._checkouts.get_connections_of(thread_name):
            pid = get_backend_pid(conn)  # debuglog
            # A cancel reaches whoever runs on the backend now: the previous
            # cancel may have waited up to _CANCEL_TIMEOUT, in which time this
            # connection can have been returned and borrowed by another thread.
            if not self._checkouts.is_held_by(conn, thread_name):
                _debug.logic("pool.cancel_skipped", backend_pid=pid, reason="rehomed")
                continue
            try:
                conn.cancel_safe(timeout=self._CANCEL_TIMEOUT)
            except Exception as exc:
                _debug.logic(
                    "pool.cancel_failed", backend_pid=pid, error=type(exc).__name__
                )
                continue
            _debug.lifecycle(
                "pool.query_cancelled", backend_pid=pid, thread=thread_name
            )
            cancelled += 1
        _debug.lifecycle("pool.queries_cancelled", thread=thread_name, count=cancelled)
        return cancelled

    def has_database(self, db_name: str) -> bool:
        with self._lock:
            return any(_get_key_dbname(k) == db_name for k in self._pools)

    def _get_keys_for_database(self, db_name: str) -> list[frozenset]:
        return [k for k in self._pools if _get_key_dbname(k) == db_name]

    def close_database(self, db_name: str) -> None:
        with self._lock:
            pools = [self._pools.pop(k) for k in self._get_keys_for_database(db_name)]
            self._probe.clear_database(db_name)
        self._close_pools(pools, db_name)

    def close_all(self) -> None:
        with self._lock:
            pools = list(self._pools.values())
            self._pools.clear()
            self._probe.clear()
        self._close_pools(pools, None)

    def _close_pools(self, pools: list[_PsycopgPool], db_name: str | None) -> None:
        for pool in pools:
            self._close_pool_safely(pool)
        if pools:
            _debug.lifecycle(
                "pool.pools_closed",
                readonly=self._readonly,
                count=len(pools),
                db=db_name or "all",
            )
            _logger.info(
                "%r: Closed %d pool(s)%s",
                self,
                len(pools),
                f" for {db_name}" if db_name else "",
            )

    def drain_database(self, db_name: str) -> None:
        with self._lock:
            pools = [self._pools[k] for k in self._get_keys_for_database(db_name)]
        self._drain_pools(pools, db_name)

    def drain_all(self) -> None:
        with self._lock:
            pools = list(self._pools.values())
        self._drain_pools(pools, None)

    def _drain_pools(self, pools: list[_PsycopgPool], db_name: str | None) -> None:
        for pool in pools:
            if not pool.closed:
                self._drain_pool_safely(pool)
        if pools:
            _debug.lifecycle(
                "pool.pools_drained",
                readonly=self._readonly,
                count=len(pools),
                db=db_name or "all",
            )
            _logger.debug(
                "%r: Drained %d pool(s)%s",
                self,
                len(pools),
                f" for {db_name}" if db_name else "",
            )

    def get_stats(self) -> dict[str, dict]:
        with self._lock:
            snapshot = list(self._pools.items())
        stats = {}
        for key, pool in snapshot:
            db_name = _get_key_dbname(key) or "unknown"
            stats[db_name] = pool.get_stats()
        return stats

    def get_health(self) -> dict:
        per_database = self.get_stats()
        with self._lock:
            n_pools = len(self._pools)
            direct_out = self._direct_out
        backends = sum(s.get("pool_size", 0) for s in per_database.values())
        backends += direct_out
        _debug.perf.count(
            "pool.health",
            readonly=self._readonly,
            databases=n_pools,
            backends=backends,
            checked_out=len(self._checkouts),
        )
        return {
            "mode": "read-only" if self._readonly else "read/write",
            "databases": n_pools,
            "backends": backends,
            "pool": self.stats.get_snapshot(
                budget=self._budget,
                direct_out=direct_out,
                pools=n_pools,
                checkouts=self._checkouts,
            ),
            "per_database": per_database,
        }
