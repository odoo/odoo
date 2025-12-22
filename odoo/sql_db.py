# Part of Odoo. See LICENSE file for full copyright and licensing details.


"""
The PostgreSQL connector is a connectivity layer between the OpenERP code and
the database, *not* a database abstraction toolkit. Database abstraction is what
the ORM does, in fact.
"""
from __future__ import annotations

import logging
import os
import re
import threading
import time
import typing
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from inspect import currentframe

import psycopg2
import psycopg2.extensions
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ
from psycopg2.pool import PoolError
from psycopg2.sql import Composable
from werkzeug import urls

import odoo
from . import tools
from .tools import SQL
from .tools.func import frame_codeinfo, locked
from .tools.misc import Callbacks

if typing.TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    T = typing.TypeVar('T')


def undecimalize(value, cr):
    if value is None:
        return None
    return float(value)

DECIMAL_TO_FLOAT_TYPE = psycopg2.extensions.new_type((1700,), 'float', undecimalize)
psycopg2.extensions.register_type(DECIMAL_TO_FLOAT_TYPE)
psycopg2.extensions.register_type(psycopg2.extensions.new_array_type((1231,), 'float[]', DECIMAL_TO_FLOAT_TYPE))

_logger = logging.getLogger(__name__)
_logger_conn = _logger.getChild("connection")

real_time = time.time.__call__  # ensure we have a non patched time for query times when using freezegun

re_from = re.compile(r'\bfrom\s+"?([a-zA-Z_0-9]+)\b', re.IGNORECASE)
re_into = re.compile(r'\binto\s+"?([a-zA-Z_0-9]+)\b', re.IGNORECASE)


def categorize_query(decoded_query):
    res_into = re_into.search(decoded_query)
    # prioritize `insert` over `select` so `select` subqueries are not
    # considered when inside a `insert`
    if res_into:
        return 'into', res_into.group(1)

    res_from = re_from.search(decoded_query)
    if res_from:
        return 'from', res_from.group(1)

    return 'other', None


sql_counter = 0

MAX_IDLE_TIMEOUT = 60 * 10


class Savepoint:
    """ Reifies an active breakpoint, allows :meth:`BaseCursor.savepoint` users
    to internally rollback the savepoint (as many times as they want) without
    having to implement their own savepointing, or triggering exceptions.

    Should normally be created using :meth:`BaseCursor.savepoint` rather than
    directly.

    The savepoint will be rolled back on unsuccessful context exits
    (exceptions). It will be released ("committed") on successful context exit.
    The savepoint object can be wrapped in ``contextlib.closing`` to
    unconditionally roll it back.

    The savepoint can also safely be explicitly closed during context body. This
    will rollback by default.

    :param BaseCursor cr: the cursor to execute the `SAVEPOINT` queries on
    """
    def __init__(self, cr):
        self.name = str(uuid.uuid1())
        self._cr = cr
        self.closed = False
        cr.execute('SAVEPOINT "%s"' % self.name)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close(rollback=exc_type is not None)

    def close(self, *, rollback=True):
        if not self.closed:
            self._close(rollback)

    def rollback(self):
        self._cr.execute('ROLLBACK TO SAVEPOINT "%s"' % self.name)

    def _close(self, rollback):
        if rollback:
            self.rollback()
        self._cr.execute('RELEASE SAVEPOINT "%s"' % self.name)
        self.closed = True


class _FlushingSavepoint(Savepoint):
    def __init__(self, cr):
        cr.flush()
        super().__init__(cr)

    def rollback(self):
        self._cr.clear()
        super().rollback()

    def _close(self, rollback):
        try:
            if not rollback:
                self._cr.flush()
        except Exception:
            rollback = True
            raise
        finally:
            super()._close(rollback)


class BaseCursor:
    """ Base class for cursors that manage pre/post commit hooks. """

    def __init__(self):
        self.precommit = Callbacks()
        self.postcommit = Callbacks()
        self.prerollback = Callbacks()
        self.postrollback = Callbacks()
        # By default a cursor has no transaction object.  A transaction object
        # for managing environments is instantiated by registry.cursor().  It
        # is not done here in order to avoid cyclic module dependencies.
        self.transaction = None

    def flush(self):
        """ Flush the current transaction, and run precommit hooks. """
        if self.transaction is not None:
            self.transaction.flush()
        self.precommit.run()

    def clear(self):
        """ Clear the current transaction, and clear precommit hooks. """
        if self.transaction is not None:
            self.transaction.clear()
        self.precommit.clear()

    def reset(self):
        """ Reset the current transaction (this invalidates more that clear()).
            This method should be called only right after commit() or rollback().
        """
        if self.transaction is not None:
            self.transaction.reset()

    def savepoint(self, flush=True) -> Savepoint:
        """context manager entering in a new savepoint

        With ``flush`` (the default), will automatically run (or clear) the
        relevant hooks.
        """
        if flush:
            return _FlushingSavepoint(self)
        else:
            return Savepoint(self)

    def __enter__(self):
        """ Using the cursor as a contextmanager automatically commits and
            closes it::

                with cr:
                    cr.execute(...)

                # cr is committed if no failure occurred
                # cr is closed in any case
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            if exc_type is None:
                self.commit()
        finally:
            self.close()


class Cursor(BaseCursor):
    """Represents an open transaction to the PostgreSQL DB backend,
       acting as a lightweight wrapper around psycopg2's
       ``cursor`` objects.

        ``Cursor`` is the object behind the ``cr`` variable used all
        over the OpenERP code.

        .. rubric:: Transaction Isolation

        One very important property of database transactions is the
        level of isolation between concurrent transactions.
        The SQL standard defines four levels of transaction isolation,
        ranging from the most strict *Serializable* level, to the least
        strict *Read Uncommitted* level. These levels are defined in
        terms of the phenomena that must not occur between concurrent
        transactions, such as *dirty read*, etc.
        In the context of a generic business data management software
        such as OpenERP, we need the best guarantees that no data
        corruption can ever be cause by simply running multiple
        transactions in parallel. Therefore, the preferred level would
        be the *serializable* level, which ensures that a set of
        transactions is guaranteed to produce the same effect as
        running them one at a time in some order.

        However, most database management systems implement a limited
        serializable isolation in the form of
        `snapshot isolation <http://en.wikipedia.org/wiki/Snapshot_isolation>`_,
        providing most of the same advantages as True Serializability,
        with a fraction of the performance cost.
        With PostgreSQL up to version 9.0, this snapshot isolation was
        the implementation of both the ``REPEATABLE READ`` and
        ``SERIALIZABLE`` levels of the SQL standard.
        As of PostgreSQL 9.1, the previous snapshot isolation implementation
        was kept for ``REPEATABLE READ``, while a new ``SERIALIZABLE``
        level was introduced, providing some additional heuristics to
        detect a concurrent update by parallel transactions, and forcing
        one of them to rollback.

        OpenERP implements its own level of locking protection
        for transactions that are highly likely to provoke concurrent
        updates, such as stock reservations or document sequences updates.
        Therefore we mostly care about the properties of snapshot isolation,
        but we don't really need additional heuristics to trigger transaction
        rollbacks, as we are taking care of triggering instant rollbacks
        ourselves when it matters (and we can save the additional performance
        hit of these heuristics).

        As a result of the above, we have selected ``REPEATABLE READ`` as
        the default transaction isolation level for OpenERP cursors, as
        it will be mapped to the desired ``snapshot isolation`` level for
        all supported PostgreSQL version (>10).

        .. attribute:: cache

            Cache dictionary with a "request" (-ish) lifecycle, only lives as
            long as the cursor itself does and proactively cleared when the
            cursor is closed.

            This cache should *only* be used to store repeatable reads as it
            ignores rollbacks and savepoints, it should not be used to store
            *any* data which may be modified during the life of the cursor.

    """
    IN_MAX = 1000   # decent limit on size of IN queries - guideline = Oracle limit

    def __init__(self, pool, dbname, dsn):
        super().__init__()
        self.sql_from_log = {}
        self.sql_into_log = {}

        # default log level determined at cursor creation, could be
        # overridden later for debugging purposes
        self.sql_log_count = 0

        # avoid the call of close() (by __del__) if an exception
        # is raised by any of the following initializations
        self._closed = True

        self.__pool = pool
        self.dbname = dbname

        self._cnx = pool.borrow(dsn)
        self._obj = self._cnx.cursor()
        if _logger.isEnabledFor(logging.DEBUG):
            self.__caller = frame_codeinfo(currentframe(), 2)
        else:
            self.__caller = False
        self._closed = False   # real initialization value
        # See the docstring of this class.
        self.connection.set_isolation_level(ISOLATION_LEVEL_REPEATABLE_READ)
        self.connection.set_session(readonly=pool.readonly)

        self.cache = {}
        self._now = None
        if os.getenv('ODOO_FAKETIME_TEST_MODE') and self.dbname in tools.config['db_name'].split(','):
            self.execute("SET search_path = public, pg_catalog;")
            self.commit()  # ensure that the search_path remains after a rollback

    def __build_dict(self, row):
        return {d.name: row[i] for i, d in enumerate(self._obj.description)}

    def dictfetchone(self):
        row = self._obj.fetchone()
        return row and self.__build_dict(row)

    def dictfetchmany(self, size):
        return [self.__build_dict(row) for row in self._obj.fetchmany(size)]

    def dictfetchall(self):
        return [self.__build_dict(row) for row in self._obj.fetchall()]

    def __del__(self):
        if not self._closed and not self._cnx.closed:
            # Oops. 'self' has not been closed explicitly.
            # The cursor will be deleted by the garbage collector,
            # but the database connection is not put back into the connection
            # pool, preventing some operation on the database like dropping it.
            # This can also lead to a server overload.
            msg = "Cursor not closed explicitly\n"
            if self.__caller:
                msg += "Cursor was created at %s:%s" % self.__caller
            else:
                msg += "Please enable sql debugging to trace the caller."
            _logger.warning(msg)
            self._close(True)

    def _format(self, query, params=None):
        encoding = psycopg2.extensions.encodings[self.connection.encoding]
        return self.mogrify(query, params).decode(encoding, 'replace')

    def mogrify(self, query, params=None):
        if isinstance(query, SQL):
            assert params is None, "Unexpected parameters for SQL query object"
            query, params = query.code, query.params
        return self._obj.mogrify(query, params)

    def execute(self, query, params=None, log_exceptions=True):
        global sql_counter

        if isinstance(query, SQL):
            assert params is None, "Unexpected parameters for SQL query object"
            query, params = query.code, query.params

        if params and not isinstance(params, (tuple, list, dict)):
            # psycopg2's TypeError is not clear if you mess up the params
            raise ValueError("SQL query parameters should be a tuple, list or dict; got %r" % (params,))

        start = real_time()
        try:
            params = params or None
            res = self._obj.execute(query, params)
        except Exception as e:
            if log_exceptions:
                _logger.error("bad query: %s\nERROR: %s", self._obj.query or query, e)
            raise
        finally:
            delay = real_time() - start
            if _logger.isEnabledFor(logging.DEBUG):
                _logger.debug("[%.3f ms] query: %s", 1000 * delay, self._format(query, params))

        # simple query count is always computed
        self.sql_log_count += 1
        sql_counter += 1

        current_thread = threading.current_thread()
        if hasattr(current_thread, 'query_count'):
            current_thread.query_count += 1
            current_thread.query_time += delay

        # optional hooks for performance and tracing analysis
        for hook in getattr(current_thread, 'query_hooks', ()):
            hook(self, query, params, start, delay)

        # advanced stats
        if _logger.isEnabledFor(logging.DEBUG):
            query_type, table = categorize_query(self._obj.query.decode())
            log_target = None
            if query_type == 'into':
                log_target = self.sql_into_log
            elif query_type == 'from':
                log_target = self.sql_from_log
            if log_target:
                stats = log_target.setdefault(table, [0, 0])
                stats[0] += 1
                stats[1] += delay * 1E6
        return res

    def execute_values(self, query, argslist, template=None, page_size=100, fetch=False):
        """
        A proxy for psycopg2.extras.execute_values which can log all queries like execute.
        But this method cannot set log_exceptions=False like execute
        """
        # Odoo Cursor only proxies all methods of psycopg2 Cursor. This is a patch for problems caused by passing
        # self instead of self._obj to the first parameter of psycopg2.extras.execute_values.
        if isinstance(query, Composable):
            query = query.as_string(self._obj)
        return psycopg2.extras.execute_values(self, query, argslist, template=template, page_size=page_size, fetch=fetch)

    def split_for_in_conditions(self, ids: Iterable[T], size: int = 0) -> Iterator[tuple[T, ...]]:
        """Split a list of identifiers into one or more smaller tuples
           safe for IN conditions, after uniquifying them."""
        return tools.misc.split_every(size or self.IN_MAX, ids)

    def print_log(self):
        global sql_counter

        if not _logger.isEnabledFor(logging.DEBUG):
            return
        def process(type):
            sqllogs = {'from': self.sql_from_log, 'into': self.sql_into_log}
            sum = 0
            if sqllogs[type]:
                sqllogitems = sqllogs[type].items()
                _logger.debug("SQL LOG %s:", type)
                for r in sorted(sqllogitems, key=lambda k: k[1]):
                    delay = timedelta(microseconds=r[1][1])
                    _logger.debug("table: %s: %s/%s", r[0], delay, r[1][0])
                    sum += r[1][1]
                sqllogs[type].clear()
            sum = timedelta(microseconds=sum)
            _logger.debug("SUM %s:%s/%d [%d]", type, sum, self.sql_log_count, sql_counter)
            sqllogs[type].clear()
        process('from')
        process('into')
        self.sql_log_count = 0

    @contextmanager
    def _enable_logging(self):
        """ Forcefully enables logging for this cursor, restores it afterwards.

        Updates the logger in-place, so not thread-safe.
        """
        level = _logger.level
        _logger.setLevel(logging.DEBUG)
        try:
            yield
        finally:
            _logger.setLevel(level)

    def close(self):
        if not self.closed:
            return self._close(False)

    def _close(self, leak=False):
        if not self._obj:
            return

        del self.cache

        # advanced stats only at logging.DEBUG level
        self.print_log()

        self._obj.close()

        # This force the cursor to be freed, and thus, available again. It is
        # important because otherwise we can overload the server very easily
        # because of a cursor shortage (because cursors are not garbage
        # collected as fast as they should). The problem is probably due in
        # part because browse records keep a reference to the cursor.
        del self._obj

        # Clean the underlying connection, and run rollback hooks.
        self.rollback()

        self._closed = True

        if leak:
            self._cnx.leaked = True
        else:
            chosen_template = tools.config['db_template']
            keep_in_pool = self.dbname not in ('template0', 'template1', 'postgres', chosen_template)
            self.__pool.give_back(self._cnx, keep_in_pool=keep_in_pool)

    def commit(self):
        """ Perform an SQL `COMMIT` """
        self.flush()
        result = self._cnx.commit()
        self.clear()
        self._now = None
        self.prerollback.clear()
        self.postrollback.clear()
        self.postcommit.run()
        return result

    def rollback(self):
        """ Perform an SQL `ROLLBACK` """
        self.clear()
        self.postcommit.clear()
        self.prerollback.run()
        result = self._cnx.rollback()
        self._now = None
        self.postrollback.run()
        return result

    def __getattr__(self, name):
        if self._closed and name == '_obj':
            raise psycopg2.InterfaceError("Cursor already closed")
        return getattr(self._obj, name)

    @property
    def closed(self):
        return self._closed or self._cnx.closed

    @property
    def readonly(self):
        return bool(self._cnx.readonly)

    def now(self):
        """ Return the transaction's timestamp ``NOW() AT TIME ZONE 'UTC'``. """
        if self._now is None:
            self.execute("SELECT (now() AT TIME ZONE 'UTC')")
            self._now = self.fetchone()[0]
        return self._now


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
    _cursors_stack = []

    def __init__(self, cursor, lock, readonly, current_test=None):
        assert isinstance(cursor, BaseCursor)
        self.current_test = current_test
        self._check('__init__')
        super().__init__()
        self._now = None
        self._closed = False
        self._cursor = cursor
        self.readonly = readonly
        # we use a lock to serialize concurrent requests
        self._lock = lock
        self._lock.acquire()
        last_cursor = self._cursors_stack and self._cursors_stack[-1]
        if last_cursor and last_cursor.readonly and not readonly and last_cursor._savepoint:
            raise Exception('Opening a read/write test cursor from a readonly one')
        self._cursors_stack.append(self)
        # in order to simulate commit and rollback, the cursor maintains a
        # savepoint at its last commit, the savepoint is created lazily
        self._savepoint = None

    def _check_savepoint(self):
        if not self._savepoint:
            # we use self._cursor._obj for the savepoint to avoid having the
            # savepoint queries in the query counts, profiler, ...
            # Those queries are tests artefacts and should be invisible.
            self._savepoint = Savepoint(self._cursor._obj)
            if self.readonly:
                # this will simulate a readonly connection
                self._cursor._obj.execute('SET TRANSACTION READ ONLY')  # use _obj to avoid impacting query count and profiler.

    def _check(self, operation):
        if self.current_test:
            self.current_test.check_test_cursor(operation)

    def execute(self, *args, **kwargs):
        assert not self._closed, "Cannot use a closed cursor"
        self._check_savepoint()
        return self._cursor.execute(*args, **kwargs)

    def close(self):
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

    def commit(self):
        """ Perform an SQL `COMMIT` """
        self._check('commit')
        self.flush()
        if self._savepoint:
            self._savepoint.close(rollback=self.readonly)
            self._savepoint = None
        self.clear()
        self.prerollback.clear()
        self.postrollback.clear()
        self.postcommit.clear()         # TestCursor ignores post-commit hooks by default

    def rollback(self):
        """ Perform an SQL `ROLLBACK` """
        self._check('rollback')
        self.clear()
        self.postcommit.clear()
        self.prerollback.run()
        if self._savepoint:
            self._savepoint.close(rollback=True)
            self._savepoint = None
        self.postrollback.run()

    def __getattr__(self, name):
        self._check(name)
        return getattr(self._cursor, name)

    def now(self):
        """ Return the transaction's timestamp ``datetime.now()``. """
        if self._now is None:
            self._now = datetime.now()
        return self._now


class PsycoConnection(psycopg2.extensions.connection):
    def lobject(*args, **kwargs):
        pass

    if hasattr(psycopg2.extensions, 'ConnectionInfo'):
        @property
        def info(self):
            class PsycoConnectionInfo(psycopg2.extensions.ConnectionInfo):
                @property
                def password(self):
                    pass
            return PsycoConnectionInfo(self)


class ConnectionPool(object):
    """ The pool of connections to database(s)

        Keep a set of connections to pg databases open, and reuse them
        to open cursors for all transactions.

        The connections are *not* automatically closed. Only a close_db()
        can trigger that.
    """
    def __init__(self, maxconn=64, readonly=False):
        self._connections = []
        self._maxconn = max(maxconn, 1)
        self._readonly = readonly
        self._lock = threading.Lock()

    def __repr__(self):
        used = len([1 for c, u, _ in self._connections[:] if u])
        count = len(self._connections)
        mode = 'read-only' if self._readonly else 'read/write'
        return f"ConnectionPool({mode};used={used}/count={count}/max={self._maxconn})"

    @property
    def readonly(self):
        return self._readonly

    def _debug(self, msg, *args):
        _logger_conn.debug(('%r ' + msg), self, *args)

    @locked
    def borrow(self, connection_info):
        """
        Borrow a PsycoConnection from the pool. If no connection is available, create a new one
        as long as there are still slots available. Perform some garbage-collection in the pool:
        idle, dead and leaked connections are removed.

        :param dict connection_info: dict of psql connection keywords
        :rtype: PsycoConnection
        """
        # free idle, dead and leaked connections
        for i, (cnx, used, last_used) in tools.reverse_enumerate(self._connections):
            if not used and not cnx.closed and time.time() - last_used > MAX_IDLE_TIMEOUT:
                self._debug('Close connection at index %d: %r', i, cnx.dsn)
                cnx.close()
            if cnx.closed:
                self._connections.pop(i)
                self._debug('Removing closed connection at index %d: %r', i, cnx.dsn)
                continue
            if getattr(cnx, 'leaked', False):
                delattr(cnx, 'leaked')
                self._connections[i][1] = False
                _logger.info('%r: Free leaked connection to %r', self, cnx.dsn)

        for i, (cnx, used, _) in enumerate(self._connections):
            if not used and self._dsn_equals(cnx.dsn, connection_info):
                try:
                    cnx.reset()
                except psycopg2.OperationalError:
                    self._debug('Cannot reset connection at index %d: %r', i, cnx.dsn)
                    # psycopg2 2.4.4 and earlier do not allow closing a closed connection
                    if not cnx.closed:
                        cnx.close()
                    continue
                self._connections[i][1] = True
                self._debug('Borrow existing connection to %r at index %d', cnx.dsn, i)

                return cnx

        if len(self._connections) >= self._maxconn:
            # try to remove the oldest connection not used
            for i, (cnx, used, _) in enumerate(self._connections):
                if not used:
                    self._connections.pop(i)
                    if not cnx.closed:
                        cnx.close()
                    self._debug('Removing old connection at index %d: %r', i, cnx.dsn)
                    break
            else:
                # note: this code is called only if the for loop has completed (no break)
                raise PoolError('The Connection Pool Is Full')

        try:
            result = psycopg2.connect(
                connection_factory=PsycoConnection,
                **connection_info)
        except psycopg2.Error:
            _logger.info('Connection to the database failed')
            raise
        self._connections.append([result, True, 0])
        self._debug('Create new connection backend PID %d', result.get_backend_pid())

        return result

    @locked
    def give_back(self, connection, keep_in_pool=True):
        self._debug('Give back connection to %r', connection.dsn)
        for i, (cnx, _, _) in enumerate(self._connections):
            if cnx is connection:
                if keep_in_pool:
                    # Release the connection and record the last time used
                    self._connections[i][1] = False
                    self._connections[i][2] = time.time()
                    self._debug('Put connection to %r in pool', cnx.dsn)
                else:
                    self._connections.pop(i)
                    self._debug('Forgot connection to %r', cnx.dsn)
                    cnx.close()
                break
        else:
            raise PoolError('This connection does not belong to the pool')

    @locked
    def close_all(self, dsn=None):
        count = 0
        last = None
        for i, (cnx, _, _) in tools.reverse_enumerate(self._connections):
            if dsn is None or self._dsn_equals(cnx.dsn, dsn):
                cnx.close()
                last = self._connections.pop(i)[0]
                count += 1
        if count:
            _logger.info('%r: Closed %d connections %s', self, count,
                        (dsn and last and 'to %r' % last.dsn) or '')

    def _dsn_equals(self, dsn1, dsn2):
        alias_keys = {'dbname': 'database'}
        ignore_keys = ['password']
        dsn1, dsn2 = ({
            alias_keys.get(key, key): str(value)
            for key, value in (psycopg2.extensions.parse_dsn(dsn) if isinstance(dsn, str) else dsn).items()
            if key not in ignore_keys
        } for dsn in (dsn1, dsn2))
        return dsn1 == dsn2


class Connection(object):
    """ A lightweight instance of a connection to postgres
    """
    def __init__(self, pool, dbname, dsn):
        self.__dbname = dbname
        self.__dsn = dsn
        self.__pool = pool

    @property
    def dsn(self):
        dsn = dict(self.__dsn)
        dsn.pop('password', None)
        return dsn

    @property
    def dbname(self):
        return self.__dbname

    def cursor(self):
        _logger.debug('create cursor to %r', self.dsn)
        return Cursor(self.__pool, self.__dbname, self.__dsn)

    def __bool__(self):
        raise NotImplementedError()

def connection_info_for(db_or_uri, readonly=False):
    """ parse the given `db_or_uri` and return a 2-tuple (dbname, connection_params)

    Connection params are either a dictionary with a single key ``dsn``
    containing a connection URI, or a dictionary containing connection
    parameter keywords which psycopg2 can build a key/value connection string
    (dsn) from

    :param str db_or_uri: database name or postgres dsn
    :param bool readonly: used to load
        the default configuration from ``db_`` or ``db_replica_``.
    :rtype: (str, dict)
    """
    if 'ODOO_PGAPPNAME' in os.environ:
        # Using manual string interpolation for security reason and trimming at default NAMEDATALEN=63
        app_name = os.environ['ODOO_PGAPPNAME'].replace('{pid}', str(os.getpid()))[0:63]
    else:
        app_name = "odoo-%d" % os.getpid()
    if db_or_uri.startswith(('postgresql://', 'postgres://')):
        # extract db from uri
        us = urls.url_parse(db_or_uri)
        if len(us.path) > 1:
            db_name = us.path[1:]
        elif us.username:
            db_name = us.username
        else:
            db_name = us.hostname
        return db_name, {'dsn': db_or_uri, 'application_name': app_name}

    connection_info = {'database': db_or_uri, 'application_name': app_name}
    for p in ('host', 'port', 'user', 'password', 'sslmode'):
        cfg = tools.config['db_' + p]
        if readonly:
            cfg = tools.config.get('db_replica_' + p, cfg)
        if cfg:
            connection_info[p] = cfg

    return db_or_uri, connection_info

_Pool = None
_Pool_readonly = None

def db_connect(to, allow_uri=False, readonly=False):
    global _Pool, _Pool_readonly  # noqa: PLW0603 (global-statement)

    maxconn = odoo.evented and tools.config['db_maxconn_gevent'] or tools.config['db_maxconn']
    if _Pool is None and not readonly:
        _Pool = ConnectionPool(int(maxconn), readonly=False)
    if _Pool_readonly is None and readonly:
        _Pool_readonly = ConnectionPool(int(maxconn), readonly=True)

    db, info = connection_info_for(to, readonly)
    if not allow_uri and db != to:
        raise ValueError('URI connections not allowed')
    return Connection(_Pool_readonly if readonly else _Pool, db, info)

def close_db(db_name):
    """ You might want to call odoo.modules.registry.Registry.delete(db_name) along this function."""
    if _Pool:
        _Pool.close_all(connection_info_for(db_name)[1])
    if _Pool_readonly:
        _Pool_readonly.close_all(connection_info_for(db_name)[1])

def close_all():
    if _Pool:
        _Pool.close_all()
    if _Pool_readonly:
        _Pool_readonly.close_all()
