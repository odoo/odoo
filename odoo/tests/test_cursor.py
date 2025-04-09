from __future__ import annotations

from datetime import datetime
import threading

from odoo.sql_db import BaseCursor, Cursor, Savepoint, _logger
import odoo


class TestCursor(BaseCursor):
    """ A pseudo-cursor to be used for tests, on top of a real cursor. It keeps
        the transaction open across requests, and simulates committing, rolling
        back, and closing:

        +------------------------+---------------------------------------------------+
        |  test cursor           | queries on actual cursor                          |
        +========================+===================================================+
        |``cr = TestCursor(...)``|                                                   |
        +------------------------+---------------------------------------------------+
        | ``cr.execute(query)``  | SAVEPOINT test_cursor_N (if not savepoint)        |
        |                        | query                                             |
        +------------------------+---------------------------------------------------+
        |  ``cr.commit()``       | RELEASE SAVEPOINT test_cursor_N (if savepoint)    |
        +------------------------+---------------------------------------------------+
        |  ``cr.rollback()``     | ROLLBACK TO SAVEPOINT test_cursor_N (if savepoint)|
        +------------------------+---------------------------------------------------+
        |  ``cr.close()``        | ROLLBACK TO SAVEPOINT test_cursor_N (if savepoint)|
        |                        | RELEASE SAVEPOINT test_cursor_N (if savepoint)    |
        +------------------------+---------------------------------------------------+
    """
    _cursors_stack: list[TestCursor] = []

    def __init__(self, cursor: Cursor, lock: threading.RLock, readonly: bool):
        assert isinstance(cursor, BaseCursor)
        super().__init__()
        self._now: datetime | None = None
        self._closed: bool = False
        self._cursor = cursor
        self.readonly = readonly
        # we use a lock to serialize concurrent requests
        self._lock = lock
        current_test = odoo.modules.module.current_test
        assert current_test, 'Test Cursor without active test ?'
        current_test.assertCanOpenTestCursor()
        lock_timeout = current_test.test_cursor_lock_timeout
        if not self._lock.acquire(timeout=lock_timeout):
            raise Exception(f'Unable to acquire lock for test cursor after {lock_timeout}s')
        try:
            # Check after acquiring in case current_test has changed.
            # This can happen if the request was hanging between two tests.
            current_test.assertCanOpenTestCursor()
            self._check_cursor_readonly()
        except Exception:
            self._lock.release()
            raise
        self._cursors_stack.append(self)
        # in order to simulate commit and rollback, the cursor maintains a
        # savepoint at its last commit, the savepoint is created lazily
        self._savepoint: Savepoint | None = None

    def _check_cursor_readonly(self):
        last_cursor = self._cursors_stack and self._cursors_stack[-1]
        if last_cursor and last_cursor.readonly and not self.readonly and last_cursor._savepoint:
            raise Exception('Opening a read/write test cursor from a readonly one')

    def _check_savepoint(self) -> None:
        if not self._savepoint:
            # we use self._cursor._obj for the savepoint to avoid having the
            # savepoint queries in the query counts, profiler, ...
            # Those queries are tests artefacts and should be invisible.
            self._savepoint = Savepoint(self._cursor._obj)
            if self.readonly:
                # this will simulate a readonly connection
                self._cursor._obj.execute('SET TRANSACTION READ ONLY')  # use _obj to avoid impacting query count and profiler.

    def execute(self, *args, **kwargs) -> None:
        assert not self._closed, "Cannot use a closed cursor"
        self._check_savepoint()
        return self._cursor.execute(*args, **kwargs)

    def close(self) -> None:
        if not self._closed:
            try:
                self.rollback()
                if self._savepoint:
                    self._savepoint.close(rollback=False)
            finally:
                self._closed = True

                tos = self._cursors_stack.pop()
                if tos is not self:
                    _logger.warning("Found different un-closed cursor when trying to close %s: %s", self, tos)
                self._lock.release()

    def commit(self) -> None:
        """ Perform an SQL `COMMIT` """
        self.flush()
        if self._savepoint:
            self._savepoint.close(rollback=self.readonly)
            self._savepoint = None
        self.clear()
        self.prerollback.clear()
        self.postrollback.clear()
        self.postcommit.clear()         # TestCursor ignores post-commit hooks by default

    def rollback(self) -> None:
        """ Perform an SQL `ROLLBACK` """
        self.clear()
        self.postcommit.clear()
        self.prerollback.run()
        if self._savepoint:
            self._savepoint.close(rollback=True)
            self._savepoint = None
        self.postrollback.run()

    def __getattr__(self, name):
        return getattr(self._cursor, name)

    def dictfetchone(self):
        """ Return the first row as a dict (column_name -> value) or None if no rows are available. """
        return self._cursor.dictfetchone()

    def dictfetchmany(self, size):
        return self._cursor.dictfetchmany(size)

    def dictfetchall(self):
        return self._cursor.dictfetchall()

    def now(self) -> datetime:
        """ Return the transaction's timestamp ``datetime.now()``. """
        if self._now is None:
            self._now = datetime.now()
        return self._now
