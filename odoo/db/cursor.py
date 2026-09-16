import logging
import threading
from collections.abc import Callable, Collection, Generator, Iterable
from contextlib import AbstractContextManager, contextmanager, suppress
from datetime import datetime
from inspect import currentframe
from time import monotonic
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Self

import psycopg
from psycopg import sql as _sql
from psycopg.pq import TransactionStatus as _TxStatus

from odoo.libs.accel import rows_to_dicts as _rows_to_dicts
from odoo.libs.datetime import real_time
from odoo.libs.debug_log import DebugLog
from odoo.libs.func import Callbacks, frame_codeinfo
from odoo.libs.sql import SQL

from .bulk import _BulkAccessMixin, _prepare_copy_in_pipeline_error
from .ddl import _has_schema_changing_statement, _inline_ddl_params, classify_statement
from .dsn import _expand_conninfo, _get_dsn_key
from .errors import (
    PG_RECOVERABLE_EXCEPTIONS,
    PG_STALE_PLAN_EXCEPTIONS,
    PG_USER_FAULT_EXCEPTIONS,
    _log_sql_error,
    has_reached_server,
    is_handled_by_seam,
    mark_failed_statement,
    mark_handled_by_seam,
    mark_stale_cached_plan,
)
from .lifecycle import clear_prepared_cache, get_backend_pid
from .metrics import _MetricsMixin, classify_query
from .pipeline import _PipelineMixin
from .pool import ConnectionPool, _get_borrow_caller
from .savepoint import Savepoint, _FlushingSavepoint
from .schema_cache import TransactionSchemaCache

if TYPE_CHECKING:
    from odoo.orm.runtime import Transaction

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_TX_IDLE = _TxStatus.IDLE
_TX_INERROR = _TxStatus.INERROR


def _get_statement_text(query: Any) -> str:
    if isinstance(query, bytes):
        try:
            return query.decode()
        except UnicodeDecodeError:
            return ""
    return query if isinstance(query, str) else str(query)


def _render_query(query: Any) -> Any:
    return query() if callable(query) else query


class BaseCursor:
    BATCH_SIZE = 1000
    _MAX_FLUSH_PASSES = 10

    _flushing_savepoint_cls: type[Savepoint] = _FlushingSavepoint

    transaction: Transaction | None
    cache: dict[Any, Any]
    dbname: str
    _savepoint_depth: int = 0
    _closed: bool = False

    def __init__(self) -> None:
        self.precommit = Callbacks()
        self.postcommit = Callbacks()
        self.prerollback = Callbacks()
        self.postrollback = Callbacks()
        self._now: datetime | None = None
        self._savepoint_depth = 0
        self.cache = {}
        self.transaction = None
        self.commit_count = 0

    def flush(self) -> None:
        passes = 0  # debuglog
        for _ in range(self._MAX_FLUSH_PASSES):
            if self.transaction is not None:
                self.transaction.flush()
            if not self.precommit:
                if _debug.pipeline.enabled and passes:
                    _debug.pipeline(
                        "cursor.flush_converged",
                        db=vars(self).get("dbname"),
                        passes=passes + 1,
                    )
                return
            _debug.pipeline(
                "cursor.flush_pass",
                db=vars(self).get("dbname"),
                pass_=passes + 1,
                precommit=len(self.precommit),
            )
            self.precommit.run()
            passes += 1  # debuglog
        if self.transaction is not None:
            self.transaction.flush()
        if self.precommit:
            _debug.logic(
                "cursor.flush_not_converged",
                db=vars(self).get("dbname"),
                passes=passes,
                precommit=len(self.precommit),
            )
            raise RuntimeError(
                f"flush() did not converge after {self._MAX_FLUSH_PASSES} "
                f"iterations: precommit hooks keep triggering new ORM changes; "
                f"committing now would silently drop pending hooks."
            )

    def clear(self) -> None:
        _debug.lifecycle(
            "cursor.cleared",
            db=vars(self).get("dbname"),
            transaction=self.transaction is not None,
            precommit_dropped=len(self.precommit),
        )
        if self.transaction is not None:
            self.transaction.clear()
        self.precommit.clear()

    def reset(self) -> None:
        _debug.lifecycle(
            "cursor.reset",
            db=vars(self).get("dbname"),
            transaction=self.transaction is not None,
        )
        if self.transaction is not None:
            self.transaction.reset()

    def invalidate_cached_plans(self) -> None:
        pass

    if TYPE_CHECKING:

        @property
        def description(self) -> list[Any] | None: ...

        def pipeline(
            self, log_exceptions: bool = True, query: Any = None
        ) -> AbstractContextManager[None]: ...

    def _before_statement(self) -> None:
        pass

    def _on_rollback_to_savepoint(self) -> None:
        pass

    def execute(
        self,
        query: str | bytes | SQL | _sql.Composable,
        params: tuple | list | dict | None = None,
        log_exceptions: bool = True,
        prepare: bool | None = None,
    ) -> None:
        raise NotImplementedError

    def commit(self) -> None:
        raise NotImplementedError

    def rollback(self) -> None:
        raise NotImplementedError

    if TYPE_CHECKING:

        def close(self) -> None:
            pass

        def fetchone(self) -> tuple[Any, ...] | None:
            pass

        def fetchall(self) -> list[tuple[Any, ...]]:
            pass

        @property
        def closed(self) -> bool:
            pass

        @property
        def rowcount(self) -> int: ...

        @property
        def connection(self) -> psycopg.Connection: ...

    def savepoint(self, flush: bool = True) -> Savepoint:
        if getattr(self, "in_pipeline", False):
            _debug.logic(
                "cursor.savepoint_refused",
                db=vars(self).get("dbname"),
                reason="in_pipeline",
                depth=self._savepoint_depth,
            )
            raise RuntimeError(
                "cannot open a savepoint inside cr.pipeline(): PostgreSQL "
                "discards every queued statement after an error, so the "
                "ROLLBACK TO SAVEPOINT is discarded too and the transaction "
                "stays aborted. Take the savepoint around the pipeline block, "
                "not inside it."
            )
        if _debug.logic.enabled:
            _debug.logic(
                "cursor.savepoint_requested",
                db=vars(self).get("dbname"),
                flush=flush,
                depth=self._savepoint_depth,
                transaction=self.transaction is not None,
                caller=_get_borrow_caller(),
            )
        if flush:
            cls = self._flushing_savepoint_cls
            if self.transaction is not None and not cls._restores_orm_state:
                _debug.logic(
                    "cursor.savepoint_refused",
                    db=vars(self).get("dbname"),
                    reason="no_orm_seam",
                    savepoint_cls=cls.__name__,
                )
                raise RuntimeError(
                    f"cursor has an ORM transaction but {cls.__name__} does not "
                    "restore ORM state on rollback; the odoo.orm.runtime savepoint "
                    "seam was not installed (import-order bug)."
                )
            return cls(self)
        return Savepoint(self)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: object,
    ) -> None:
        _debug.lifecycle(
            "cursor.context_exit",
            db=vars(self).get("dbname"),
            commit=exc_type is None and not self._closed,
            error=None if exc_type is None else exc_type.__name__,
        )
        try:
            if exc_type is None and not self._closed:
                self.commit()
        finally:
            self.close()

    def fetchscalar(self) -> Any:
        row = self.fetchone()
        return row[0] if row else None

    def dictfetchone(self) -> dict[str, Any] | None:
        raise NotImplementedError

    def dictfetchmany(self, size: int) -> list[dict[str, Any]]:
        res: list[dict[str, Any]] = []
        while size > 0 and (row := self.dictfetchone()) is not None:
            res.append(row)
            size -= 1
        return res

    def dictfetchall(self) -> list[dict[str, Any]]:
        res: list[dict[str, Any]] = []
        while (row := self.dictfetchone()) is not None:
            res.append(row)
        return res

    def now(self) -> datetime:
        if self._now is None:
            self.execute("SELECT (now() AT TIME ZONE 'UTC')")
            row = self.fetchone()
            assert row is not None, "SELECT now() returned no row"
            self._now = row[0]
            _debug.perf.count("cursor.now_fetched", db=vars(self).get("dbname"))
        return self._now


class Cursor(_BulkAccessMixin, _MetricsMixin, _PipelineMixin, BaseCursor):
    _closed: bool = True
    _statement_timeout: float | None = None
    _statement_timeout_armed: bool = False
    _statement_timeout_depth: int = 0

    __caller: tuple[str | None, int | str] | Literal[False]

    def __init__(
        self,
        pool: ConnectionPool,
        dbname: str,
        dsn: dict,
        key: frozenset | None = None,
        *,
        borrow_timeout: float | None = None,
        fail_fast: bool = False,
    ):
        super().__init__()
        self._init_metrics_state()

        self._closed: bool = True

        self.__pool: ConnectionPool = pool
        self.dbname = dbname
        self._dsn = dsn
        self._key = key
        self._transaction_touched = False
        self._commit_write_observer: Callable[[], None] | None = None

        self._schema_cache = TransactionSchemaCache()
        self._schema_changed = False

        self._init_pipeline_state()

        self._thread = threading.current_thread()

        self._cnx: psycopg.Connection = pool.borrow(
            dsn, key=key, timeout=borrow_timeout, fail_fast=fail_fast
        )
        try:
            self._obj: psycopg.Cursor = self._cnx.cursor()
            if _logger.isEnabledFor(logging.DEBUG):
                self.__caller = frame_codeinfo(currentframe(), 2)
            else:
                self.__caller = False
            self._readonly = bool(pool.readonly)

            self._closed = False
            if _debug.lifecycle.enabled:
                _debug.lifecycle(
                    "cursor.opened",
                    db=dbname,
                    readonly=self._readonly,
                    thread=self._thread.name,
                    backend_pid=self._backend_pid,
                    caller=_get_borrow_caller(),
                )
        except BaseException:
            obj = self.__dict__.get("_obj")
            if obj is not None:
                with suppress(Exception):
                    obj.close()
            keep_in_pool = self._is_connection_clean()
            _debug.lifecycle(
                "cursor.open_failed",
                db=dbname,
                readonly=vars(self).get("_readonly"),
                keep_in_pool=keep_in_pool,
            )
            pool.give_back(self._cnx, keep_in_pool=keep_in_pool)
            raise

    @property
    def _backend_pid(self) -> int | None:  # debuglog
        return get_backend_pid(vars(self).get("_cnx"))

    def _fetchall(self) -> list[tuple[Any, ...]]:
        obj = self._obj
        if self._pipeline is not None:
            return self._wait_in_pipeline(obj.fetchall)
        return obj.fetchall()

    def _fetchmany(self, size: int) -> list[tuple[Any, ...]]:
        obj = self._obj
        if self._pipeline is not None:
            return self._wait_in_pipeline(obj.fetchmany, size)
        return obj.fetchmany(size)

    def dictfetchone(self) -> dict[str, Any] | None:
        row = self.fetchone()
        if row is None:
            return None
        return {
            col.name: val for col, val in zip(self._obj.description, row, strict=True)
        }

    def _get_column_names(self) -> tuple[str, ...]:
        return tuple(col.name for col in self._obj.description)

    def _rows_to_dict_list(self, rows: list[tuple[Any, ...]]) -> list[dict[str, Any]]:
        return _rows_to_dicts(self._get_column_names(), rows)

    def dictfetchmany(self, size: int) -> list[dict[str, Any]]:
        if size <= 0:
            return []
        rows = self._fetchmany(size)
        _debug.perf.count(
            "cursor.fetch", shape="dictfetchmany", rows=len(rows), size=size
        )
        if not rows:
            return []
        return self._rows_to_dict_list(rows)

    def dictfetchall(self) -> list[dict[str, Any]]:
        rows = self._fetchall()
        _debug.perf.count("cursor.fetch", shape="dictfetchall", rows=len(rows))
        if not rows:
            return []
        return self._rows_to_dict_list(rows)

    def fetchone(self) -> tuple[Any, ...] | None:
        obj = self._obj
        if self._pipeline is not None:
            return self._wait_in_pipeline(obj.fetchone)
        return obj.fetchone()

    def fetchall(self) -> list[tuple[Any, ...]]:
        rows = self._fetchall()
        _debug.perf.count("cursor.fetch", shape="fetchall", rows=len(rows))
        return rows

    def fetchmany(self, size: int = 0) -> list[tuple[Any, ...]]:
        rows = self._fetchmany(size)
        _debug.perf.count("cursor.fetch", shape="fetchmany", rows=len(rows), size=size)
        return rows

    @property
    def description(self) -> list[Any] | None:
        self._sync_pipeline_results()
        return self._obj.description

    @property
    def rowcount(self) -> int:
        self._sync_pipeline_results()
        return self._obj.rowcount

    def nextset(self) -> bool | None:
        self._sync_pipeline_results()
        return self._obj.nextset()

    @contextmanager
    def copy(
        self,
        statement: str | bytes | _sql.Composable,
        params: tuple | list | dict | None = None,
        *,
        writer: Any = None,
    ) -> Generator[Any]:
        if self._pipeline is not None:
            _debug.logic("cursor.copy_refused", db=self.dbname, reason="in_pipeline")
            raise _prepare_copy_in_pipeline_error("cr.copy()")
        self._before_statement()
        hooks = getattr(self._thread, "query_hooks", None)
        start = real_time() if hooks else 0.0
        t0 = monotonic()
        counts = False
        _debug.pipeline(
            "cursor.copy_opened",
            db=self.dbname,
            custom_writer=writer is not None,
            in_pipeline=self._pipeline is not None,
        )
        try:
            with self._obj.copy(statement, params, writer=writer) as copy:
                yield copy
            counts = True
        except Exception as e:
            counts = self._statement_failed(e, statement, label="COPY", prepared=False)
            raise
        finally:
            self._statement_done(
                monotonic() - t0,
                counts=counts,
                query=statement,
                params=params,
                label="COPY",
                hooks=hooks,
                start=start,
                debug=_logger.isEnabledFor(logging.DEBUG),
            )

    def _prepare_copy_refused_error(self) -> TypeError:
        return TypeError(
            f"{type(self).__name__} cannot be copied: it owns a borrowed pooled "
            f"connection and an open transaction.  A shallow copy shares "
            f"``_obj``/``_cnx``, so the copy's ``__del__`` would roll back and "
            f"return the connection to the pool while the original is still "
            f"using it (and log a spurious 'Cursor not closed explicitly').  "
            f"Pass the cursor around, or open a second one via "
            f"``registry.cursor()``."
        )

    def __copy__(self) -> NoReturn:
        raise self._prepare_copy_refused_error()

    def __deepcopy__(self, memo: dict) -> NoReturn:
        raise self._prepare_copy_refused_error()

    def __del__(self) -> None:
        if self._closed:
            return
        msg = "Cursor not closed explicitly\n"
        if self.__caller:
            msg += f"Cursor was created at {self.__caller[0]}:{self.__caller[1]}"
        else:
            msg += "Please enable sql debugging to trace the caller."
        _logger.warning(msg)
        _debug.lifecycle(
            "cursor.not_closed_explicitly",
            db=vars(self).get("dbname"),
            caller=self.__caller and f"{self.__caller[0]}:{self.__caller[1]}",
            connection_closed=self._cnx.closed,
        )
        if self._cnx.closed:
            self._closed = True
            del self._obj
            self.__pool.give_back(self._cnx, keep_in_pool=False)
            return
        self._close()

    # A connection lost before the transaction's first statement completed is
    # replayed on a fresh borrow: nothing has happened server-side, so the
    # statement is the same request it was. Once a statement has run, a
    # savepoint is open or psycopg's pipeline has been entered (the block's
    # second statement; the first is an ordinary statement, and the ORM's
    # flush opens such a block), the transaction has state only the caller
    # can rebuild, and the loss propagates as it did.
    def _replace_lost_connection(self, exc: Exception) -> bool:
        refused = (
            "not_a_loss"
            if not isinstance(exc, psycopg.OperationalError)
            or not (self._cnx.closed or not has_reached_server(exc))
            else "touched"
            if self._transaction_touched
            else "savepoint"
            if self._savepoint_depth
            else "pipeline"
            if self._pipeline is not None
            else None
        )
        if refused is not None:
            if _debug.logic.enabled and refused != "not_a_loss":
                _debug.logic(
                    "cursor.replay_refused",
                    db=self.dbname,
                    reason=refused,
                    error=type(exc).__name__,
                    sqlstate=getattr(exc, "sqlstate", None),
                )
            return False
        pool = self.__pool
        old, old_obj = self._cnx, self._obj
        with suppress(Exception):
            old_obj.close()
        del self._obj
        # The dead connection goes back first: its permit is the one the
        # replacement needs when the budget is spent (maxconn=1 is the limit
        # case). A replacement that still cannot be had ends the cursor --
        # its connection is gone and nothing is left to give back -- and the
        # loss propagates, not a PoolError dressed as a statement error.
        pool.give_back(old, keep_in_pool=False)
        try:
            replacement = pool.borrow(self._dsn, key=self._key)
        except Exception as borrow_exc:
            self._closed = True
            _debug.logic(
                "cursor.connection_not_replaced",
                db=self.dbname,
                error=type(borrow_exc).__name__,
            )
            return False
        try:
            obj = replacement.cursor()
            if self._readonly and not pool.readonly:
                replacement.read_only = True
        except BaseException:
            pool.give_back(replacement, keep_in_pool=False)
            self._closed = True
            raise
        self._cnx, self._obj = replacement, obj
        _debug.lifecycle(
            "cursor.connection_replaced",
            db=self.dbname,
            error=type(exc).__name__,
            sqlstate=getattr(exc, "sqlstate", None),
        )
        self._reset_transaction_caches()
        self._pipeline_pending = False
        if self._statement_timeout is not None:
            self._arm_statement_timeout()
        _logger.warning(
            "Connection to %s lost before the transaction's first statement "
            "completed (%s); replayed on a fresh connection",
            self.dbname,
            exc,
        )
        return True

    # `txid_current_if_assigned()` is non-NULL exactly when this transaction
    # wrote (an xid is assigned on the first write), so one round trip at
    # commit answers "did it write" without classifying a single statement.
    # Asked only when someone registered an observer and something ran.
    def on_commit_if_written(self, observer: Callable[[], None]) -> None:
        self._commit_write_observer = observer

    def _has_written(self) -> bool:
        self.execute("SELECT txid_current_if_assigned() IS NOT NULL")
        row = self.fetchone()
        written = bool(row and row[0])
        _debug.logic("cursor.commit_write_asked", db=self.dbname, written=written)
        return written

    def cancel(self) -> None:
        _debug.lifecycle("cursor.cancel", db=self.dbname, backend_pid=self._backend_pid)
        self._cnx.cancel_safe()

    # The budget belongs to the cursor, not to one transaction: `SET LOCAL`
    # dies at every commit and rollback, and a savepoint rollback reverts one
    # issued inside it, so the cursor re-arms it before the next statement.
    # Arming does not count as touching the transaction: the replay re-arms
    # on the replacement connection, so nothing is lost with the old one.
    def set_statement_timeout(self, seconds: float | None) -> None:
        previous, self._statement_timeout = self._statement_timeout, seconds or None
        _debug.logic(
            "cursor.statement_timeout",
            db=self.dbname,
            seconds=self._statement_timeout,
            previous=previous,
            armed=self._statement_timeout_armed,
            touched=self._transaction_touched,
        )
        # Mid-transaction the change applies now; a budget that was set is
        # lifted now even when a savepoint rollback disarmed it, because the
        # arming may have been outside that savepoint (test cursors nest
        # savepoints this cursor does not count).
        if self._statement_timeout_armed or (
            self._transaction_touched and (previous or seconds)
        ):
            self._arm_statement_timeout()

    def _arm_statement_timeout(self) -> None:
        seconds = self._statement_timeout
        self._statement_timeout_armed = seconds is not None
        self._statement_timeout_depth = self._savepoint_depth
        touched = self._transaction_touched
        value = f"{int(seconds * 1000)}ms" if seconds else "0"
        _debug.logic(
            "cursor.statement_timeout_armed",
            db=self.dbname,
            value=value,
            savepoint_depth=self._savepoint_depth,
        )
        self.execute("SET LOCAL statement_timeout = %s", (value,))
        self._transaction_touched = touched

    def _before_statement(self) -> None:
        if self._statement_timeout is not None and not self._statement_timeout_armed:
            self._arm_statement_timeout()

    def _statement_failed(
        self,
        exc: Exception,
        query: Any,
        *,
        label: str = "query",
        log_exceptions: bool = True,
        prepared: bool = True,
    ) -> bool:
        if is_handled_by_seam(exc):
            _debug.logic(
                "cursor.statement_seam_short_circuit",
                db=vars(self).get("dbname"),
                label=label,
                error=type(exc).__name__,
            )
            return has_reached_server(exc)
        mark_handled_by_seam(exc)
        if prepared:
            self._invalidate_cached_plans_if_stale(exc)
        if log_exceptions or isinstance(exc, PG_USER_FAULT_EXCEPTIONS):
            rendered = _render_query(query)
            if isinstance(exc, PG_USER_FAULT_EXCEPTIONS):
                mark_failed_statement(exc, _get_statement_text(rendered))
            if log_exceptions:
                _log_sql_error(exc, rendered, label=label)
        _debug.logic(
            "cursor.statement_failed",
            db=vars(self).get("dbname"),
            backend_pid=self._backend_pid,
            label=label,
            error=type(exc).__name__,
            sqlstate=getattr(exc, "sqlstate", None),
            reached_server=has_reached_server(exc),
            recoverable=isinstance(exc, PG_RECOVERABLE_EXCEPTIONS),
            user_fault=isinstance(exc, PG_USER_FAULT_EXCEPTIONS),
            logged=log_exceptions,
            in_pipeline=vars(self).get("_pipeline") is not None,
            savepoint_depth=vars(self).get("_savepoint_depth"),
        )
        return has_reached_server(exc)

    def _statement_done(
        self,
        delay: float,
        *,
        counts: bool,
        query: Any,
        params: Any = None,
        count: int = 1,
        label: str = "query",
        hooks: Any = None,
        start: float = 0.0,
        debug: bool = False,
    ) -> None:
        if debug:
            rows = f" ({count} rows)" if count != 1 else ""
            _logger.debug(
                "[%.3f ms] %s%s: %s",
                1000 * delay,
                label,
                rows,
                self._format_statement(_render_query(query), params),
            )
        if _debug.perf.enabled:
            qs = _get_statement_text(_render_query(query))  # debuglog
            query_type, table = classify_query(qs)  # debuglog
            words = qs.split(None, 1)  # debuglog
            _debug.perf.count(
                "cursor.statement",
                db=vars(self).get("dbname"),
                backend_pid=self._backend_pid,
                label=label,
                head=words[0][:12].upper() if words else "",
                kind=query_type,
                table=table,
                ms=delay * 1000.0,
                rows=count,
                ok=counts,
                in_pipeline=vars(self).get("_pipeline") is not None,
            )
        if counts:
            self._transaction_touched = True
            self._record_metrics(
                delay,
                count,
                query=_render_query(query) if hooks else None,
                params=params,
                start=start,
                hooks=hooks,
            )
        if self._pipeline_depth:
            self._pipeline_statement_time += delay

    def execute(
        self,
        query: str | bytes | SQL | _sql.Composable,
        params: tuple | list | dict | None = None,
        log_exceptions: bool = True,
        prepare: bool | None = None,
    ) -> None:

        self._before_statement()

        if isinstance(query, SQL):
            if params is not None:
                raise ValueError(
                    "Unexpected parameters combined with a SQL query object"
                )
            params = query.params
            query = query.code
        else:
            if isinstance(query, _sql.Composable):
                query = query.as_string(self._cnx)
            if params and not isinstance(params, (tuple, list, dict)):
                raise ValueError(
                    f"SQL query parameters should be a tuple, list or dict; got {params!r}"
                )

        query, params, prepare, qs, ddl_kw, rollback_to = self._prepare_ddl_statement(
            query, params, prepare
        )

        if self._pipeline_stack is not None:
            self._arm_pipeline()

        debug = _logger.isEnabledFor(logging.DEBUG)
        hooks = getattr(self._thread, "query_hooks", None)
        start = real_time() if hooks else 0.0
        obj = self._obj
        t0 = monotonic()
        counts = False
        try:
            try:
                obj.execute(query, params, prepare=prepare)
            except Exception as e:
                if not self._replace_lost_connection(e):
                    raise
                self._obj.execute(query, params, prepare=prepare)
            counts = True
            self._pipeline_pending = self._pipeline is not None
        except Exception as e:
            counts = self._statement_failed(
                e, query, log_exceptions=log_exceptions, prepared=prepare is not False
            )
            raise
        finally:
            delay = monotonic() - t0
            self._statement_done(
                delay,
                counts=counts,
                query=query,
                params=params,
                hooks=hooks,
                start=start,
                debug=debug,
            )

        self._after_statement(qs, ddl_kw, rollback_to, delay, debug)

    def _after_statement(
        self, qs: str, ddl_kw: str | None, rollback_to: bool, delay: float, debug: bool
    ) -> None:
        if _has_schema_changing_statement(qs, ddl_kw):
            self._invalidate_caches_after_ddl()
        elif rollback_to:
            self._on_rollback_to_savepoint()
        if debug:
            query_type, table = classify_query(qs)
            self._record_sql_log(query_type, table, delay)

    def _prepare_ddl_statement(
        self,
        query: Any,
        params: tuple | list | dict | None,
        prepare: bool | None,
    ) -> tuple[Any, tuple | list | dict | None, bool | None, str, str | None, bool]:
        qs = _get_statement_text(query)
        ddl_kw, rollback_to = classify_statement(qs)
        if ddl_kw is not None:
            inlined = bool(params)  # debuglog
            if params:
                query = _inline_ddl_params(qs, params, self._cnx)
                params = None
            if prepare is None:
                prepare = False
            if _debug.logic.enabled:
                _debug.logic(
                    "cursor.ddl_classified",
                    db=vars(self).get("dbname"),
                    keyword=ddl_kw,
                    params_inlined=inlined,
                    prepare=prepare,
                    schema_changing=_has_schema_changing_statement(qs, ddl_kw),
                )
        return query, params, prepare, qs, ddl_kw, rollback_to

    def invalidate_cached_plans(self) -> None:
        cleared = clear_prepared_cache(self._cnx)
        _debug.lifecycle(
            "cursor.prepared_cache", db=vars(self).get("dbname"), cleared=cleared
        )
        if not cleared:
            _logger.warning(
                "psycopg no longer exposes Connection._prepared.clear(); "
                "auto-prepare is off for the rest of this cursor's life "
                "(restored when the connection returns to the pool). "
                "Re-check odoo.db.cursor against the installed psycopg.",
            )
            self._cnx.prepare_threshold = None
            self.execute("DEALLOCATE ALL")
        self._schema_cache.invalidate_catalog_facts()

    def _on_rollback_to_savepoint(self) -> None:
        _debug.lifecycle(
            "cursor.savepoint_rollback_seen",
            db=vars(self).get("dbname"),
            depth=self._savepoint_depth,
            locked_tables=len(self._schema_cache.locked_tables),
        )
        self._schema_cache.release_locks_since_depth(self._savepoint_depth)
        if self._savepoint_depth <= self._statement_timeout_depth:
            self._statement_timeout_armed = False

    def _mark_table_locked(self, table: str) -> None:
        self._schema_cache.mark_locked(table, self._savepoint_depth)

    def _invalidate_cached_plans_if_stale(self, exc: Exception) -> bool:
        if not isinstance(exc, PG_STALE_PLAN_EXCEPTIONS):
            return False
        prepared = getattr(self._cnx, "_prepared", None)
        if prepared is None or not getattr(prepared, "_names", None):
            _debug.logic(
                "cursor.stale_plan_ignored",
                db=vars(self).get("dbname"),
                error=type(exc).__name__,
                reason="no_prepared_statements",
            )
            return False
        clear_prepared_cache(self._cnx)
        self._schema_cache.invalidate_catalog_facts()
        mark_stale_cached_plan(exc)
        _debug.logic(
            "cursor.stale_plan_invalidated",
            db=vars(self).get("dbname"),
            error=type(exc).__name__,
        )
        self._drain_siblings_after_stale_plan()
        return True

    # A stale plan this connection met came from a schema change this process
    # did not see land -- a DBA's ALTER, another process's migration -- so the
    # idle siblings hold the same stale plans and each would burn a retry of
    # its own. One drain per database per window heals them together; the
    # window keeps a burst of requests from draining the pool once each.
    _STALE_PLAN_DRAIN_INTERVAL = 5.0
    _stale_plan_drains: dict[str, float] = {}

    def _drain_siblings_after_stale_plan(self) -> None:
        now = monotonic()
        last = self._stale_plan_drains.get(self.dbname, 0.0)
        if now - last < self._STALE_PLAN_DRAIN_INTERVAL:
            _debug.logic("cursor.stale_plan_drain_throttled", db=self.dbname)
            return
        self._stale_plan_drains[self.dbname] = now
        _logger.info(
            "Stale cached plan on %s: a schema change landed outside this "
            "process; draining its idle connections",
            self.dbname,
        )
        self._drain_sibling_connections()

    def _drain_sibling_connections(self) -> None:
        from . import drain_db

        with _debug.perf("cursor.drain_siblings", db=self.dbname):
            drain_db(self.dbname)

    def _invalidate_caches_after_ddl(self) -> None:
        _debug.logic("cursor.ddl_detected", db=vars(self).get("dbname"))
        self.invalidate_cached_plans()
        self._schema_changed = True

    def executemany(
        self,
        query: str | SQL | _sql.Composable,
        params_seq: Iterable[tuple | list | dict],
        returning: bool = False,
        log_exceptions: bool = True,
    ) -> None:
        self._before_statement()

        if isinstance(query, SQL):
            if query.params:
                raise ValueError(
                    "executemany does not support SQL objects with embedded "
                    "params; pass the per-row params via params_seq instead."
                )
            query = query.code
        elif isinstance(query, _sql.Composable):
            query = query.as_string(self._cnx)

        qs = _get_statement_text(query)
        ddl_kw, rollback_to = classify_statement(qs)

        rows: Collection[tuple | list | dict] = (
            params_seq if isinstance(params_seq, Collection) else list(params_seq)
        )
        if not rows:
            _debug.logic("cursor.executemany_empty", db=self.dbname)
            return

        if ddl_kw is not None and any(rows):
            _debug.logic(
                "cursor.executemany_refused",
                db=self.dbname,
                reason="parameterised_ddl",
                keyword=ddl_kw,
            )
            raise ValueError(
                f"executemany() cannot run parameterised DDL ({ddl_kw}); "
                f"DDL takes no bound parameters. Issue it once with "
                f"cr.execute(), which inlines them."
            )

        if self._pipeline_stack is not None:
            self._arm_pipeline()

        debug = _logger.isEnabledFor(logging.DEBUG)
        hooks = getattr(self._thread, "query_hooks", None)
        start = real_time() if hooks else 0.0
        obj = self._obj
        t0 = monotonic()
        counts = False
        try:
            try:
                obj.executemany(query, rows, returning=returning)
            except Exception as e:
                if not self._replace_lost_connection(e):
                    raise
                self._obj.executemany(query, rows, returning=returning)
            counts = True
            self._pipeline_pending = self._pipeline is not None
        except Exception as e:
            counts = self._statement_failed(e, query, log_exceptions=log_exceptions)
            raise
        finally:
            delay = monotonic() - t0
            self._statement_done(
                delay,
                counts=counts,
                query=query,
                count=len(rows),
                hooks=hooks,
                start=start,
                debug=debug,
            )

        self._after_statement(qs, ddl_kw, rollback_to, delay, debug)

    def close(self) -> None:
        if not self._closed:
            self._close()

    def _close(self) -> None:
        keep_in_pool = True
        try:
            try:
                self.cache.clear()
                self.log_sql_stats()
            finally:
                try:
                    self._rollback()
                except Exception as exc:
                    keep_in_pool = self._is_connection_clean()
                    _debug.logic(
                        "cursor.close_rollback_failed",
                        db=vars(self).get("dbname"),
                        error=type(exc).__name__,
                        keep_in_pool=keep_in_pool,
                        reached_server=has_reached_server(exc),
                    )
                    if keep_in_pool:
                        _logger.warning("Failed to roll back on cursor close")
                    elif not has_reached_server(exc):
                        _logger.warning(
                            "Discarding a connection whose backend is gone: %s",
                            exc,
                        )
                    else:
                        _logger.exception(
                            "Failed to roll back on cursor close; discarding connection"
                        )
            self._obj.close()
        finally:
            self._closed = True
            del self._obj
            if _debug.lifecycle.enabled:
                state = vars(self)  # debuglog
                _debug.lifecycle(
                    "cursor.closed",
                    db=state.get("dbname"),
                    backend_pid=self._backend_pid,
                    keep_in_pool=keep_in_pool,
                    commits=state.get("commit_count"),
                    statements=state.get("sql_statement_count"),
                )
            self.__pool.give_back(self._cnx, keep_in_pool=keep_in_pool)

    def _get_transaction_status(self) -> _TxStatus | None:
        try:
            return self._cnx.info.transaction_status
        except Exception:
            return None

    def _is_connection_clean(self) -> bool:
        return self._get_transaction_status() == _TX_IDLE

    def in_failed_transaction(self) -> bool:
        return self._get_transaction_status() == _TX_INERROR

    def enforce_readonly(self) -> None:
        if self._readonly:
            return
        self._cnx.read_only = True
        self._readonly = True
        _debug.lifecycle("cursor.readonly_enforced", db=vars(self).get("dbname"))

    def commit(self) -> None:
        if self._closed:
            _debug.logic(
                "cursor.commit_refused", db=vars(self).get("dbname"), reason="closed"
            )
            raise psycopg.InterfaceError("Cursor already closed")
        if self._savepoint_depth:
            _debug.logic(
                "cursor.commit_refused",
                db=self.dbname,
                reason="in_savepoint",
                depth=self._savepoint_depth,
            )
            raise RuntimeError(
                "Cannot commit inside a savepoint! "
                "This would corrupt the savepoint's rollback state."
            )
        _debug.pipeline(
            "cursor.commit_started",
            db=self.dbname,
            precommit=len(self.precommit),
            postcommit=len(self.postcommit),
            in_pipeline=self._pipeline is not None,
        )
        with _debug.perf("cursor.commit.flush", cr=self, db=self.dbname):
            self.flush()
        observer = self._commit_write_observer
        # A failed transaction cannot be asked anything, and COMMIT on one is
        # a rollback the server performs quietly; asking would turn that into
        # InFailedSqlTransaction.
        written = (
            observer is not None
            and self._transaction_touched
            and not self.in_failed_transaction()
            and self._has_written()
        )
        with _debug.perf("cursor.commit.sync", db=self.dbname):
            self._cnx.commit()
        if written and observer is not None:
            observer()
        self.commit_count += 1
        _debug.lifecycle(
            "cursor.committed",
            db=self.dbname,
            backend_pid=self._backend_pid,
            commits=self.commit_count,
            schema_changed=self._schema_changed,
            postcommit=len(self.postcommit),
        )
        if self._schema_changed:
            self._schema_changed = False
            self._drain_sibling_connections()
        self.clear()
        self._reset_transaction_caches()
        self.prerollback.clear()
        self.postrollback.clear()
        with _debug.perf(
            "cursor.commit.postcommit",
            cr=self,
            db=self.dbname,
            hooks=len(self.postcommit),
        ):
            self.postcommit.run()

    def rollback(self) -> None:
        if self._closed:
            _debug.logic(
                "cursor.rollback_refused",
                db=vars(self).get("dbname"),
                reason="closed",
            )
            raise psycopg.InterfaceError("Cursor already closed")
        if self._savepoint_depth:
            _debug.logic(
                "cursor.rollback_refused",
                db=self.dbname,
                reason="in_savepoint",
                depth=self._savepoint_depth,
            )
            raise RuntimeError(
                "Cannot rollback inside a savepoint! "
                "Use cr.savepoint() for nested transaction control."
            )
        self._rollback()

    def _rollback(self) -> None:
        _debug.lifecycle(
            "cursor.rollback",
            db=self.dbname,
            backend_pid=self._backend_pid,
            prerollback=len(self.prerollback),
            postrollback=len(self.postrollback),
        )
        self.clear()
        self.postcommit.clear()
        try:
            with _debug.perf(
                "cursor.rollback.prerollback",
                cr=self,
                db=self.dbname,
                hooks=len(self.prerollback),
            ):
                self.prerollback.run()
        finally:
            with _debug.perf(
                "cursor.rollback.sync",
                db=self.dbname,
                schema_changed_dropped=self._schema_changed,
            ):
                self._cnx.rollback()
            self._schema_changed = False
            self._reset_transaction_caches()
        with _debug.perf(
            "cursor.rollback.postrollback",
            cr=self,
            db=self.dbname,
            hooks=len(self.postrollback),
        ):
            self.postrollback.run()

    def _reset_transaction_caches(self) -> None:
        self._schema_cache.clear()
        self._now = None
        self._transaction_touched = False
        self._statement_timeout_armed = False

    def __getattr__(self, name: str) -> Any:
        if name.startswith("__") and name.endswith("__"):
            raise AttributeError(name)
        _debug.logic(
            "cursor.attribute_refused",
            db=vars(self).get("dbname"),
            name=name,
            closed=self._closed,
        )
        if self._closed:
            msg = "Cursor already closed"
            raise psycopg.InterfaceError(msg)
        raise AttributeError(
            f"Cursor.{name} is not part of the Odoo cursor API. "
            f"Add explicit forwarding in cursor.py, or reach psycopg deliberately "
            f"with cr._obj.{name}."
        )

    @property
    def closed(self) -> bool:
        return self._closed or bool(self._cnx.closed)

    @property
    def connection(self) -> psycopg.Connection:
        return self._cnx

    @property
    def readonly(self) -> bool:
        return self._readonly


class Connection:
    __slots__ = ("__dbname", "__dsn", "__key", "__pool")

    def __init__(self, pool: ConnectionPool, dbname: str, dsn: dict):
        self.__dbname = dbname
        self.__dsn = dict(dsn)
        self.__pool = pool
        self.__key = _get_dsn_key(dsn)

    @property
    def dsn(self) -> dict:
        dsn = _expand_conninfo(self.__dsn)
        dsn.pop("password", None)
        return dsn

    @property
    def dbname(self) -> str:
        return self.__dbname

    def cursor(
        self, *, borrow_timeout: float | None = None, fail_fast: bool = False
    ) -> Cursor:
        if _logger.isEnabledFor(logging.DEBUG):
            _logger.debug("create cursor to %r", self.dsn)
        _debug.pipeline(
            "cursor.requested",
            db=self.__dbname,
            readonly=self.__pool.readonly,
            thread=threading.current_thread().name,
            borrow_timeout=borrow_timeout,
            fail_fast=fail_fast,
        )
        return Cursor(
            self.__pool,
            self.__dbname,
            self.__dsn,
            key=self.__key,
            borrow_timeout=borrow_timeout,
            fail_fast=fail_fast,
        )


if TYPE_CHECKING:
    from .bulk import _CursorInternals

    def _assert_cursor_satisfies_bulk_host(_c: Cursor) -> _CursorInternals:
        return _c

    from .metrics import _MetricsHost

    def _assert_cursor_satisfies_metrics_host(_c: Cursor) -> _MetricsHost:
        return _c

    from .pipeline import _PipelineHost

    def _assert_cursor_satisfies_pipeline_host(_c: Cursor) -> _PipelineHost:
        return _c
