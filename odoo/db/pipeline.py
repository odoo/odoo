from __future__ import annotations

import logging
from collections.abc import Callable, Generator
from contextlib import ExitStack, contextmanager
from time import monotonic
from typing import TYPE_CHECKING, Any

import psycopg

from odoo.libs.debug_log import DebugLog

from .errors import has_reached_server
from .pool import _get_borrow_caller

if TYPE_CHECKING:
    from typing import Protocol

    class _PipelineHost(Protocol):
        _cnx: psycopg.Connection
        _pipeline_depth: int
        _pipeline_stack: ExitStack | None
        _pipeline: psycopg.Pipeline | None
        _pipeline_statements: int
        _pipeline_statement_time: float
        _pipeline_wait_time: float
        _pipeline_exit_started: float
        _pipeline_pending: bool
        _savepoint_depth: int
        dbname: str

        def _wait_in_pipeline[T](self, wait: Callable[..., T], *args: Any) -> T: ...
        def _mark_pipeline_exit_started(self) -> None: ...

        def _statement_failed(
            self,
            exc: Exception,
            query: Any,
            *,
            label: str = "query",
            log_exceptions: bool = True,
            prepared: bool = True,
        ) -> bool: ...
        def _record_metrics(
            self,
            delay: float,
            count: int = 1,
            *,
            statement: bool = True,
            query: Any = None,
            params: Any = None,
            start: float = 0.0,
            hooks: Any = None,
        ) -> None: ...


_logger = logging.getLogger("odoo.db.cursor")
_debug = DebugLog("odoo.db.cursor")


class _PipelineMixin:
    _pipeline_depth: int
    _pipeline_stack: ExitStack | None
    _pipeline: psycopg.Pipeline | None
    _pipeline_statements: int
    _pipeline_statement_time: float
    _pipeline_wait_time: float
    _pipeline_exit_started: float
    _pipeline_pending: bool

    def _init_pipeline_state(self: _PipelineHost) -> None:
        self._pipeline_depth = 0
        self._pipeline_stack = None
        self._pipeline = None
        self._pipeline_statements = 0
        self._pipeline_statement_time = 0.0
        self._pipeline_wait_time = 0.0
        self._pipeline_exit_started = 0.0
        self._pipeline_pending = False

    def _wait_in_pipeline[T](
        self: _PipelineHost, wait: Callable[..., T], *args: Any
    ) -> T:
        t0 = monotonic()
        try:
            result = wait(*args)
        finally:
            self._pipeline_wait_time += monotonic() - t0
        self._pipeline_pending = False
        return result

    def _sync_pipeline_results(self: _PipelineHost) -> None:
        if self._pipeline_pending and (pipeline := self._pipeline) is not None:
            _debug.pipeline("cursor.pipeline_synced_for_result", db=self.dbname)
            self._wait_in_pipeline(pipeline.sync)

    @property
    def in_pipeline(self: _PipelineHost) -> bool:
        return self._pipeline is not None

    def _arm_pipeline(self: _PipelineHost) -> None:
        self._pipeline_statements += 1
        if self._pipeline_statements == 2 and self._pipeline_stack is not None:
            self._pipeline = self._pipeline_stack.enter_context(self._cnx.pipeline())
            self._pipeline_stack.callback(self._mark_pipeline_exit_started)
            _debug.lifecycle("cursor.pipeline_entered", db=self.dbname)

    def _mark_pipeline_exit_started(self: _PipelineHost) -> None:
        self._pipeline_exit_started = monotonic()

    @contextmanager
    def pipeline(
        self: _PipelineHost, log_exceptions: bool = True, query: Any = None
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
                entered=self._pipeline is not None,
                statement_ms=self._pipeline_statement_time * 1000.0,
                wait_ms=waited * 1000.0,
                error=failed,
            )
            self._pipeline_stack = None
            self._pipeline = None
            self._pipeline_depth = 0
            self._pipeline_pending = False
