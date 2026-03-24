from __future__ import annotations

import typing
from datetime import datetime

import odoo.modules
from odoo.sql_db import Cursor, Savepoint, _logger

if typing.TYPE_CHECKING:
    import threading
    from odoo.sql_db import PsycoConnection as _base_PsycoConnection
else:
    _base_PsycoConnection = object


class TestCursor(Cursor):
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
    _cnx: MockedPsycoConnection

    def __init__(self, cursor: Cursor, lock: threading.RLock, readonly: bool):
        assert isinstance(cursor, Cursor) and not isinstance(cursor, TestCursor)
        super().__init__(MockedPsycoConnection(cursor, readonly), cursor.dbname)
        self._closed = True  # consider closed until acquired
        self._cnx._obj = self._obj
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
            if (
                self._cursors_stack
                and (last_cursor := self._cursors_stack[-1])
                and last_cursor.readonly
                and not self._cnx.readonly
                and last_cursor._cnx._savepoint
            ):
                raise Exception('Opening a read/write test cursor from a readonly one')  # noqa: TRY301
        except Exception:
            self._lock.release()
            raise
        self._closed = False
        self._cursors_stack.append(self)

    def execute(self, *args, **kwargs) -> None:
        assert not self.closed, "Cannot use a closed cursor"
        if self._now is None:
            self._now = datetime.now()
        self._cnx._check_savepoint()
        return super().execute(*args, **kwargs)

    def close(self):
        if self._closed:
            return
        try:
            super().close()
        finally:
            tos = self._cursors_stack.pop()
            if tos is not self:
                _logger.warning("Found different un-closed cursor when trying to close %s: %s", self, tos)
            self._cnx._cursor.sql_log_count += self.sql_log_count  # propagate stats to the main cursor
            self._lock.release()

    def commit(self) -> None:
        """ Perform an SQL `COMMIT` """
        self.precommit.add(self.postcommit.clear)  # ignore post-commit hooks
        super().commit()

    def rollback(self) -> None:
        super().rollback()
        # rollback again to release the savepoint that may be created during
        # reset of the registry (after the rollback) which may perform queries
        self._cnx.rollback()

    def now(self) -> datetime:
        """ Return the transaction's timestamp ``datetime.now()``. """
        if self._now is None:
            self._now = datetime.now()
        return self._now


class MockedPsycoConnection(_base_PsycoConnection):
    def __init__(self, cursor: Cursor, readonly: bool):
        self._cursor = cursor
        self.readonly = readonly
        # In order to simulate commit and rollback, the connection maintains a
        # savepoint at its last commit. This savepoint is created lazily.
        self._savepoint: Savepoint | None = None
        self._obj = None

    def set_session(self, *a, **kw):
        pass  # ignoring

    def give_back(self, keep_in_pool=True):
        del self._obj

    def _check_savepoint(self) -> None:
        if self._savepoint:
            return
        # We use self._obj for the savepoint to avoid having the savepoint
        # queries in the query counts, profiler, etc. Those queries are tests
        # artefacts and should be invisible.
        obj = self._obj
        self._savepoint = Savepoint(obj)
        if self.readonly:
            # this will simulate a readonly connection
            obj.execute('SET TRANSACTION READ ONLY')

    def commit(self):
        if self._savepoint is not None:
            # readonly transaction must rollback the read only flag
            # in any case, no changes have been made
            self._savepoint.close(rollback=self.readonly)
            self._savepoint = None

    def rollback(self):
        if self._savepoint is not None:
            self._savepoint.close(rollback=True)
            self._savepoint = None

    def reset(self):
        self.rollback()

    @property
    def closed(self) -> bool:
        return self._cursor.closed

    def __getattr__(self, name):
        return getattr(self._cursor._cnx, name)
