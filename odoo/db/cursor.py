import logging
import threading
from collections.abc import Callable, Collection, Generator, Iterable
from contextlib import AbstractContextManager, ExitStack, contextmanager, suppress
from datetime import datetime
from inspect import currentframe
from time import monotonic
from typing import TYPE_CHECKING, Any, Literal, NoReturn, Self

import psycopg
from psycopg import IsolationLevel
from psycopg import sql as _sql
from psycopg.pq import TransactionStatus as _TxStatus

from odoo.libs.accel import rows_to_dicts as _rows_to_dicts
from odoo.libs.datetime import real_time
from odoo.libs.debug_log import DebugLog
from odoo.libs.func import Callbacks, frame_codeinfo
from odoo.libs.sql import SQL

from .bulk import _BulkAccessMixin
from .ddl import _has_schema_changing_statement, _inline_ddl_params, classify_statement
from .errors import (
    PG_RECOVERABLE_EXCEPTIONS,
    PG_STALE_PLAN_EXCEPTIONS,
    PG_USER_FAULT_EXCEPTIONS,
    _log_sql_error,
    has_reached_server,
    is_handled_by_seam,
    mark_handled_by_seam,
    mark_stale_cached_plan,
)
from .lifecycle import clear_prepared_cache
from .metrics import _MetricsMixin, classify_query
from .pool import ConnectionPool, _get_borrow_caller
from .savepoint import Savepoint, _FlushingSavepoint
from .schema_cache import TransactionSchemaCache

if TYPE_CHECKING:
    from odoo.orm.runtime import Transaction

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)

_TX_IDLE = _TxStatus.IDLE


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


class Cursor(_BulkAccessMixin, _MetricsMixin, BaseCursor):
    _closed: bool = True

    __caller: tuple[str | None, int | str] | Literal[False]

    def __init__(
        self,
        pool: ConnectionPool,
        dbname: str,
        dsn: dict,
        key: frozenset | None = None,
    ):
        super().__init__()
        self._init_metrics_state()

        self._closed: bool = True

        self.__pool: ConnectionPool = pool
        self.dbname = dbname

        self._schema_cache = TransactionSchemaCache()
        self._schema_changed = False

        self._pipeline_depth = 0
        self._pipeline_stack: ExitStack | None = None
        self._pipeline: psycopg.Pipeline | None = None
        self._pipeline_statements = 0
        self._pipeline_entered = False
        self._pipeline_statement_time = 0.0
        self._pipeline_wait_time = 0.0
        self._pipeline_exit_started = 0.0
        self._pipeline_pending = False

        self._thread = threading.current_thread()

        self._cnx: psycopg.Connection = pool.borrow(dsn, key=key)
        self._backend_pid = getattr(  # debuglog
            getattr(self._cnx, "info", None), "backend_pid", None
        )
        try:
            self._obj: psycopg.Cursor = self._cnx.cursor()
            if _logger.isEnabledFor(logging.DEBUG):
                self.__caller = frame_codeinfo(currentframe(), 2)
            else:
                self.__caller = False
            self._cnx.isolation_level = IsolationLevel.REPEATABLE_READ
            self._cnx.read_only = pool.readonly
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
                readonly=bool(getattr(pool, "readonly", None)),
                keep_in_pool=keep_in_pool,
            )
            pool.give_back(self._cnx, keep_in_pool=keep_in_pool)
            raise

    def _wait_in_pipeline[T](self, wait: Callable[..., T], *args: Any) -> T:
        t0 = monotonic()
        try:
            result = wait(*args)
        finally:
            self._pipeline_wait_time += monotonic() - t0
        self._pipeline_pending = False
        return result

    def _sync_pipeline_results(self) -> None:
        pipeline = self._pipeline
        if pipeline is not None and self._pipeline_pending:
            _debug.pipeline("cursor.pipeline_synced_for_result", db=self.dbname)
            self._wait_in_pipeline(pipeline.sync)

    def _fetchall(self) -> list[tuple[Any, ...]]:
        obj = self._obj
        if self._pipeline_entered:
            return self._wait_in_pipeline(obj.fetchall)
        return obj.fetchall()

    def _fetchmany(self, size: int) -> list[tuple[Any, ...]]:
        obj = self._obj
        if self._pipeline_entered:
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
        if self._pipeline_entered:
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
        if self._pipeline_entered:
            self._sync_pipeline_results()
        return self._obj.description

    @property
    def rowcount(self) -> int:
        if self._pipeline_entered:
            self._sync_pipeline_results()
        return self._obj.rowcount

    def nextset(self) -> bool | None:
        return self._obj.nextset()

    @contextmanager
    def copy(
        self,
        statement: str | bytes | _sql.Composable,
        params: tuple | list | dict | None = None,
        *,
        writer: Any = None,
    ) -> Generator[Any]:
        self._before_statement()
        hooks = getattr(self._thread, "query_hooks", None)
        start = real_time() if hooks else 0.0
        t0 = monotonic()
        counts = False
        _debug.pipeline(
            "cursor.copy_opened",
            db=self.dbname,
            custom_writer=writer is not None,
            in_pipeline=self._pipeline_entered,
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
        if not self._closed and not self._cnx.closed:
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
            )
            self._close()

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
        if log_exceptions:
            _log_sql_error(exc, _render_query(query), label=label)
        _debug.logic(
            "cursor.statement_failed",
            db=vars(self).get("dbname"),
            backend_pid=vars(self).get("_backend_pid"),
            label=label,
            error=type(exc).__name__,
            sqlstate=getattr(exc, "sqlstate", None),
            reached_server=has_reached_server(exc),
            recoverable=isinstance(exc, PG_RECOVERABLE_EXCEPTIONS),
            user_fault=isinstance(exc, PG_USER_FAULT_EXCEPTIONS),
            logged=log_exceptions,
            in_pipeline=vars(self).get("_pipeline_entered"),
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
                backend_pid=vars(self).get("_backend_pid"),
                label=label,
                head=words[0][:12].upper() if words else "",
                kind=query_type,
                table=table,
                ms=delay * 1000.0,
                rows=count,
                ok=counts,
                in_pipeline=vars(self).get("_pipeline_entered"),
            )
        if counts:
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
            code, embedded = query.code, query.params
            query, params = code, embedded
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
            obj.execute(query, params, prepare=prepare)
            counts = True
            self._pipeline_pending = self._pipeline_entered
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

        self._after_statement(qs, ddl_kw, rollback_to)

        if debug:
            query_type, table = classify_query(qs)
            self._record_sql_log(query_type, table, delay)

    def _after_statement(self, qs: str, ddl_kw: str | None, rollback_to: bool) -> None:
        if _has_schema_changing_statement(qs, ddl_kw):
            self._invalidate_caches_after_ddl()
        elif rollback_to:
            self._on_rollback_to_savepoint()

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
        if not clear_prepared_cache(self._cnx):
            _logger.warning(
                "psycopg no longer exposes Connection._prepared.clear(); "
                "auto-prepare is off for the rest of this cursor's life "
                "(restored when the connection returns to the pool). "
                "Re-check odoo.db.cursor against the installed psycopg.",
            )
            self._cnx.prepare_threshold = None
            self.execute("DEALLOCATE ALL")
            _debug.logic("cursor.prepared_cache_fallback", db=vars(self).get("dbname"))
        else:
            _debug.lifecycle(
                "cursor.prepared_cache_cleared", db=vars(self).get("dbname")
            )
        self._schema_cache.invalidate_catalog_facts()

    def _on_rollback_to_savepoint(self) -> None:
        _debug.lifecycle(
            "cursor.savepoint_rollback_seen",
            db=vars(self).get("dbname"),
            depth=self._savepoint_depth,
            locked_tables=len(self._schema_cache.locked_tables),
        )
        self._schema_cache.release_locks_since_depth(self._savepoint_depth)

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
        return True

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
            obj.executemany(query, rows, returning=returning)
            counts = True
            self._pipeline_pending = self._pipeline_entered
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

        self._after_statement(qs, ddl_kw, rollback_to)

        if debug:
            query_type, table = classify_query(qs)
            self._record_sql_log(query_type, table, delay)

    @property
    def in_pipeline(self) -> bool:
        return self._pipeline_entered

    def _arm_pipeline(self) -> None:
        self._pipeline_statements += 1
        if self._pipeline_statements == 2 and self._pipeline_stack is not None:
            self._pipeline = self._pipeline_stack.enter_context(self._cnx.pipeline())
            self._pipeline_stack.callback(self._mark_pipeline_exit_started)
            self._pipeline_entered = True
            _debug.lifecycle("cursor.pipeline_entered", db=self.dbname)

    def _mark_pipeline_exit_started(self) -> None:
        self._pipeline_exit_started = monotonic()

    @contextmanager
    def pipeline(
        self, log_exceptions: bool = True, query: Any = None
    ) -> Generator[None]:
        if self._pipeline_depth:
            self._pipeline_depth += 1
            _debug.lifecycle(
                "cursor.pipeline_nested", db=self.dbname, depth=self._pipeline_depth
            )
            try:
                yield
            finally:
                self._pipeline_depth -= 1
            return

        self._pipeline_depth = 1
        self._pipeline_statements = 0
        self._pipeline_statement_time = 0.0
        self._pipeline_wait_time = 0.0
        self._pipeline_exit_started = 0.0
        failed = None  # debuglog
        if _debug.pipeline.enabled:
            _debug.pipeline(
                "cursor.pipeline_opened",
                db=self.dbname,
                savepoint_depth=self._savepoint_depth,
                query_given=query is not None,
                caller=_get_borrow_caller(),
            )
        try:
            with ExitStack() as stack:
                self._pipeline_stack = stack
                yield
        except Exception as e:
            failed = type(e).__name__  # debuglog
            if has_reached_server(e):
                self._statement_failed(
                    e,
                    query
                    if query is not None
                    else "<pipelined statement; psycopg does not report which>",
                    label="pipelined statement",
                    log_exceptions=log_exceptions,
                )
            raise
        finally:
            if self._pipeline_exit_started:
                self._pipeline_wait_time += monotonic() - self._pipeline_exit_started
            waited = self._pipeline_wait_time
            if waited > 0:
                self._record_metrics(waited, count=0, statement=False)
            _debug.perf.count(
                "cursor.pipeline",
                db=self.dbname,
                statements=self._pipeline_statements,
                entered=self._pipeline_entered,
                statement_ms=self._pipeline_statement_time * 1000.0,
                wait_ms=waited * 1000.0,
                error=failed,
            )
            self._pipeline_stack = None
            self._pipeline = None
            self._pipeline_depth = 0
            self._pipeline_entered = False
            self._pipeline_pending = False

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
                    backend_pid=state.get("_backend_pid"),
                    keep_in_pool=keep_in_pool,
                    commits=state.get("commit_count"),
                    statements=state.get("sql_statement_count"),
                )
            self.__pool.give_back(self._cnx, keep_in_pool=keep_in_pool)

    def _is_connection_clean(self) -> bool:
        try:
            return self._cnx.info.transaction_status == _TX_IDLE
        except Exception:
            return False

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
            in_pipeline=self._pipeline_entered,
        )
        with _debug.perf("cursor.commit.flush", cr=self, db=self.dbname):
            self.flush()
        with _debug.perf("cursor.commit.sync", db=self.dbname):
            self._cnx.commit()
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
        self._schema_cache.clear()
        self._now = None
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
            self._schema_cache.clear()
        self._now = None
        with _debug.perf(
            "cursor.rollback.postrollback",
            cr=self,
            db=self.dbname,
            hooks=len(self.postrollback),
        ):
            self.postrollback.run()

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


if TYPE_CHECKING:
    from .bulk import _CursorInternals

    def _assert_cursor_satisfies_bulk_host(_c: Cursor) -> _CursorInternals:
        return _c

    from .metrics import _MetricsHost

    def _assert_cursor_satisfies_metrics_host(_c: Cursor) -> _MetricsHost:
        return _c
