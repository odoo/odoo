import contextlib
import logging
import threading
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, cast

import psycopg

import odoo
from odoo.db import BaseCursor, Cursor, Savepoint
from odoo.libs.debug_log import DebugLog

if TYPE_CHECKING:
    from .common import BaseCase

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def _release_foreign_acquisition(lock: Any) -> None:
    if hasattr(lock, "_owner"):
        foreign = lock._owner not in (None, threading.get_ident())
        if foreign:
            lock._owner = threading.get_ident()
            lock._count = 1
        lock.release()
        _debug.logic("test.lock.stranded_released", adopted=foreign)
        return
    try:
        lock.release()
    except RuntimeError:
        _debug.logic("test.lock.stranded_release_failed")
        _logger.warning(
            "Could not release the lock of a stranded test cursor: another "
            "thread holds it and this lock exposes no owner to adopt, so every "
            "later test cursor will stall for test_cursor_lock_timeout",
        )


class TestCursor(BaseCursor):
    __test__ = False

    _cursors_stack: list[TestCursor] = []

    @classmethod
    def release_stranded(cls, owner: str = "") -> int:
        stranded = cls._cursors_stack
        if stranded:
            _debug.lifecycle(
                "test.cursor.stranded", owner=owner or None, count=len(stranded)
            )
        for cursor in reversed(stranded):
            cursor.abandon(owner)
        cls._cursors_stack = []
        return len(stranded)

    def abandon(self, owner: str = "") -> None:
        _logger.warning(
            "A cursor was remaining in the TestCursor stack at the end of %s; "
            "releasing its registry lock",
            owner or "the test",
        )
        try:
            self._close_savepoint(rollback=True)
        except Exception as exc:
            _debug.logic(
                "test.cursor.stranded_rollback_failed",
                owner=owner or None,
                error=type(exc).__name__,
            )
            _logger.warning(
                "Could not roll back the savepoint of the cursor stranded by %s",
                owner or "the test",
                exc_info=True,
            )
        self._closed = True
        _release_foreign_acquisition(self._lock)

    def __init__(self, cursor: Cursor, lock: threading.RLock, readonly: bool) -> None:
        if not isinstance(cursor, BaseCursor):
            raise TypeError(
                f"TestCursor wraps a BaseCursor, got {type(cursor).__name__}"
            )
        super().__init__()
        self._closed: bool = False
        self._cursor = cursor
        self.readonly: bool = readonly
        self._lock = lock
        running = odoo.modules.module.current_test
        if isinstance(running, bool):
            raise RuntimeError(
                "TestCursor opened with no test running: odoo.modules.module."
                "current_test is not set"
            )
        current_test = cast("BaseCase", running)
        current_test.assertCanOpenTestCursor()
        lock_timeout = current_test.test_cursor_lock_timeout
        with _debug.perf(
            "test.cursor.lock_wait",
            test=current_test.canonical_tag,
            timeout=lock_timeout,
            held=getattr(lock, "count", None),
        ) as span:
            acquired = self._lock.acquire(timeout=lock_timeout)
            span.set(acquired=acquired)
        if not acquired:
            _debug.logic(
                "test.cursor.lock_timeout",
                test=current_test.canonical_tag,
                timeout=lock_timeout,
                depth=len(self._cursors_stack),
            )
            raise TimeoutError(
                f"Unable to acquire lock for test cursor after {lock_timeout}s"
            )
        try:
            current_test.assertCanOpenTestCursor()
            self._check_cursor_readonly()
            self._check_outer_savepoints()
        except Exception as exc:
            _debug.lifecycle(
                "test.cursor.open_refused",
                test=current_test.canonical_tag,
                error=type(exc).__name__,
            )
            self._lock.release()
            raise
        self._cursors_stack.append(self)
        self._savepoint: Savepoint | None = None
        _debug.lifecycle(
            "test.cursor.open",
            test=current_test.canonical_tag,
            readonly=readonly,
            depth=len(self._cursors_stack),
            held=getattr(lock, "count", None),
        )

    def _check_cursor_readonly(self) -> None:
        if self.readonly:
            return
        if any(cursor.readonly and cursor._savepoint for cursor in self._cursors_stack):
            _debug.logic(
                "test.cursor.readonly_violation", depth=len(self._cursors_stack)
            )
            raise RuntimeError("Opening a read/write test cursor from a readonly one")

    def _check_outer_savepoints(self) -> None:
        # Every test cursor shares one connection, and a cursor takes its savepoint on
        # its first statement. An outer cursor whose first statement runs while this one
        # is open would nest its savepoint inside ours, and our rollback would destroy it.
        # Read-only cursors stay lazy: their savepoint sets the transaction read-only.
        forced = 0  # debuglog
        for cursor in self._cursors_stack:
            if not cursor.readonly:
                if not cursor._savepoint:
                    forced += 1  # debuglog
                cursor._check_savepoint()
        if _debug.logic.enabled and forced:
            _debug.logic(
                "test.cursor.outer_savepoints_forced",
                forced=forced,
                depth=len(self._cursors_stack),
            )

    def _check_savepoint(self) -> None:
        if not self._savepoint:
            self._savepoint = Savepoint(self._cursor._obj)
            if self.readonly:
                self._cursor._obj.execute("SET TRANSACTION READ ONLY")
            _debug.lifecycle("test.cursor.savepoint_opened", readonly=self.readonly)

    def _close_savepoint(self, *, rollback: bool) -> None:
        if not self._savepoint:
            return
        self._savepoint.close(rollback=rollback)
        self._savepoint = None
        _debug.lifecycle("test.cursor.savepoint_closed", rollback=rollback)
        if rollback:
            self._cursor._on_rollback_to_savepoint()

    def _statement(self, name: str, args: tuple, kwargs: dict) -> Any:
        if self._closed:
            raise psycopg.InterfaceError("Cursor already closed")
        self._check_savepoint()
        _debug.perf.count("test.cursor.statement", kind=name, readonly=self.readonly)
        return getattr(self._cursor, name)(*args, **kwargs)

    def execute(self, *args: Any, **kwargs: Any) -> None:
        return self._statement("execute", args, kwargs)

    def executemany(self, *args: Any, **kwargs: Any) -> None:
        return self._statement("executemany", args, kwargs)

    def execute_values(self, *args: Any, **kwargs: Any) -> Any:
        return self._statement("execute_values", args, kwargs)

    def copy_from(self, *args: Any, **kwargs: Any) -> Any:
        return self._statement("copy_from", args, kwargs)

    def copy(self, *args: Any, **kwargs: Any) -> Any:
        return self._statement("copy", args, kwargs)

    def close(self) -> None:
        if self._closed:
            _debug.logic("test.cursor.close_again")
            return
        try:
            self.rollback()
            # A statement budget lives as long as its cursor; here the real
            # cursor outlives every test cursor, so the budget ends with this one.
            if getattr(self._cursor, "_statement_timeout", None) is not None:
                self._cursor.set_statement_timeout(None)
        finally:
            self._closed = True

            in_order = bool(self._cursors_stack and self._cursors_stack[-1] is self)
            if in_order:
                self._cursors_stack.pop()
            else:
                _debug.logic(
                    "test.cursor.close_out_of_order",
                    depth=len(self._cursors_stack),
                    on_stack=self in self._cursors_stack,
                )
                _logger.warning(
                    "Out-of-order close: %s is not the top of the cursor stack",
                    self,
                )
                with contextlib.suppress(ValueError):
                    self._cursors_stack.remove(self)
            self._lock.release()
            _debug.lifecycle(
                "test.cursor.close",
                readonly=self.readonly,
                in_order=in_order,
                depth=len(self._cursors_stack),
                commits=self.commit_count,
                held=getattr(self._lock, "count", None),
            )

    def commit(self) -> None:
        self.flush()
        self._close_savepoint(rollback=self.readonly)
        self.commit_count += 1
        self.clear()
        self._now = None
        self.prerollback.clear()
        self.postrollback.clear()
        self.postcommit.clear()
        _debug.lifecycle(
            "test.cursor.commit", readonly=self.readonly, commits=self.commit_count
        )

    def rollback(self) -> None:
        had_savepoint = self._savepoint is not None  # debuglog
        self.clear()
        self._now = None
        self.postcommit.clear()
        self.prerollback.run()
        self._close_savepoint(rollback=True)
        self.postrollback.run()
        _debug.lifecycle(
            "test.cursor.rollback", readonly=self.readonly, had_savepoint=had_savepoint
        )

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)

    def dictfetchone(self) -> dict | None:
        return self._cursor.dictfetchone()

    def dictfetchmany(self, size: int) -> list[dict]:
        return self._cursor.dictfetchmany(size)

    def dictfetchall(self) -> list[dict]:
        return self._cursor.dictfetchall()

    def now(self) -> datetime:
        if self._now is None:
            self._now = datetime.now(UTC).replace(tzinfo=None)
        return self._now
