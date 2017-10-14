# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


"""
The PostgreSQL connector is a connectivity layer between the OpenERP code and
the database, *not* a database abstraction toolkit. Database abstraction is what
the ORM does, in fact.
"""

from contextlib import contextmanager
from functools import wraps
import logging
import time
import urlparse
import uuid

import psycopg2
import psycopg2.extras
import psycopg2.extensions
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_REPEATABLE_READ
from psycopg2.pool import PoolError

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

_logger = logging.getLogger(__name__)

types_mapping = {
    'date': (1082,),
    'time': (1083,),
    'datetime': (1114,),
}

def unbuffer(symb, cr):
    if symb is None:
        return None
    return str(symb)

def undecimalize(symb, cr):
    if symb is None:
        return None
    return float(symb)

for name, typeoid in types_mapping.items():
    psycopg2.extensions.register_type(psycopg2.extensions.new_type(typeoid, name, lambda x, cr: x))
psycopg2.extensions.register_type(psycopg2.extensions.new_type((700, 701, 1700,), 'float', undecimalize))


import tools

from tools import parse_version as pv
if pv(psycopg2.__version__) < pv('2.7'):
    from psycopg2._psycopg import QuotedString
    def adapt_string(adapted):
        """Python implementation of psycopg/psycopg2#459 from v2.7"""
        if '\x00' in adapted:
            raise ValueError("A string literal cannot contain NUL (0x00) characters.")
        return QuotedString(adapted)

    psycopg2.extensions.register_adapter(str, adapt_string)
    psycopg2.extensions.register_adapter(unicode, adapt_string)

from tools.func import frame_codeinfo
from datetime import timedelta
import threading
from inspect import currentframe

import re
re_from = re.compile('.* from "?([a-zA-Z_0-9]+)"? .*$')
re_into = re.compile('.* into "?([a-zA-Z_0-9]+)"? .*$')

sql_counter = 0

class Cursor(object):
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
        all supported PostgreSQL version (8.3 - 9.x).

        Note: up to psycopg2 v.2.4.2, psycopg2 itself remapped the repeatable
        read level to serializable before sending it to the database, so it would
        actually select the new serializable mode on PostgreSQL 9.1. Make
        sure you use psycopg2 v2.4.2 or newer if you use PostgreSQL 9.1 and
        the performance hit is a concern for you.

        .. attribute:: cache

            Cache dictionary with a "request" (-ish) lifecycle, only lives as
            long as the cursor itself does and proactively cleared when the
            cursor is closed.

            This cache should *only* be used to store repeatable reads as it
            ignores rollbacks and savepoints, it should not be used to store
            *any* data which may be modified during the life of the cursor.

    """
    IN_MAX = 1000   # decent limit on size of IN queries - guideline = Oracle limit

    def check(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if self._closed:
                msg = 'Unable to use a closed cursor.'
                if self.__closer:
                    msg += ' It was closed at %s, line %s' % self.__closer
                raise psycopg2.OperationalError(msg)
            return f(self, *args, **kwargs)
        return wrapper

    def __init__(self, pool, dbname, dsn, serialized=True):
        self.sql_from_log = {}
        self.sql_into_log = {}

        # default log level determined at cursor creation, could be
        # overridden later for debugging purposes
        self.sql_log = _logger.isEnabledFor(logging.DEBUG)

        self.sql_log_count = 0

        # avoid the call of close() (by __del__) if an exception
        # is raised by any of the following initialisations
        self._closed = True

        self.__pool = pool
        self.dbname = dbname
        # Whether to enable snapshot isolation level for this cursor.
        # see also the docstring of Cursor.
        self._serialized = serialized

        self._cnx = pool.borrow(dsn)
        self._obj = self._cnx.cursor()
        if self.sql_log:
            self.__caller = frame_codeinfo(currentframe(), 2)
        else:
            self.__caller = False
        self._closed = False   # real initialisation value
        self.autocommit(False)
        self.__closer = False

        self._default_log_exceptions = True

        self.cache = {}

        # event handlers, see method after() below
        self._event_handlers = {'commit': [], 'rollback': []}

    def __build_dict(self, row):
        return {d.name: row[i] for i, d in enumerate(self._obj.description)}
    def dictfetchone(self):
        row = self._obj.fetchone()
        return row and self.__build_dict(row)
    def dictfetchmany(self, size):
        return map(self.__build_dict, self._obj.fetchmany(size))
    def dictfetchall(self):
        return map(self.__build_dict, self._obj.fetchall())

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

    @check
    def execute(self, query, params=None, log_exceptions=None):
        if params and not isinstance(params, (tuple, list, dict)):
            # psycopg2's TypeError is not clear if you mess up the params
            raise ValueError("SQL query parameters should be a tuple, list or dict; got %r" % (params,))

        if self.sql_log:
            now = time.time()
            _logger.debug("query: %s", query)

        try:
            params = params or None
            res = self._obj.execute(query, params)
        except Exception:
            if self._default_log_exceptions if log_exceptions is None else log_exceptions:
                _logger.info("bad query: %s", self._obj.query or query)
            raise

        # simple query count is always computed
        self.sql_log_count += 1

        # advanced stats only if sql_log is enabled
        if self.sql_log:
            delay = (time.time() - now) * 1E6

            res_from = re_from.match(query.lower())
            if res_from:
                self.sql_from_log.setdefault(res_from.group(1), [0, 0])
                self.sql_from_log[res_from.group(1)][0] += 1
                self.sql_from_log[res_from.group(1)][1] += delay
            res_into = re_into.match(query.lower())
            if res_into:
                self.sql_into_log.setdefault(res_into.group(1), [0, 0])
                self.sql_into_log[res_into.group(1)][0] += 1
                self.sql_into_log[res_into.group(1)][1] += delay
        return res

    def split_for_in_conditions(self, ids, size=None):
        """Split a list of identifiers into one or more smaller tuples
           safe for IN conditions, after uniquifying them."""
        return tools.misc.split_every(size or self.IN_MAX, ids)

    def print_log(self):
        global sql_counter

        if not self.sql_log:
            return
        def process(type):
            sqllogs = {'from': self.sql_from_log, 'into': self.sql_into_log}
            sum = 0
            if sqllogs[type]:
                sqllogitems = sqllogs[type].items()
                sqllogitems.sort(key=lambda k: k[1][1])
                _logger.debug("SQL LOG %s:", type)
                sqllogitems.sort(lambda x, y: cmp(x[1][0], y[1][0]))
                for r in sqllogitems:
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
        self.sql_log = False

    @check
    def close(self):
        return self._close(False)

    def _close(self, leak=False):
        global sql_counter

        if not self._obj:
            return

        del self.cache

        if self.sql_log:
            self.__closer = frame_codeinfo(currentframe(), 3)

        # simple query count is always computed
        sql_counter += self.sql_log_count

        # advanced stats only if sql_log is enabled
        self.print_log()

        self._obj.close()

        # This force the cursor to be freed, and thus, available again. It is
        # important because otherwise we can overload the server very easily
        # because of a cursor shortage (because cursors are not garbage
        # collected as fast as they should). The problem is probably due in
        # part because browse records keep a reference to the cursor.
        del self._obj
        self._closed = True

        # Clean the underlying connection.
        self._cnx.rollback()

        if leak:
            self._cnx.leaked = True
        else:
            chosen_template = tools.config['db_template']
            templates_list = tuple(set(['template0', 'template1', 'postgres', chosen_template]))
            keep_in_pool = self.dbname not in templates_list
            self.__pool.give_back(self._cnx, keep_in_pool=keep_in_pool)

    @check
    def autocommit(self, on):
        if on:
            isolation_level = ISOLATION_LEVEL_AUTOCOMMIT
        else:
            # If a serializable cursor was requested, we
            # use the appropriate PotsgreSQL isolation level
            # that maps to snaphsot isolation.
            # For all supported PostgreSQL versions (8.3-9.x),
            # this is currently the ISOLATION_REPEATABLE_READ.
            # See also the docstring of this class.
            # NOTE: up to psycopg 2.4.2, repeatable read
            #       is remapped to serializable before being
            #       sent to the database, so it is in fact
            #       unavailable for use with pg 9.1.
            isolation_level = \
                ISOLATION_LEVEL_REPEATABLE_READ \
                if self._serialized \
                else ISOLATION_LEVEL_READ_COMMITTED
        self._cnx.set_isolation_level(isolation_level)

    @check
    def after(self, event, func):
        """ Register an event handler.

            :param event: the event, either `'commit'` or `'rollback'`
            :param func: a callable object, called with no argument after the
                event occurs

            Be careful when coding an event handler, since any operation on the
            cursor that was just committed/rolled back will take place in the
            next transaction that has already begun, and may still be rolled
            back or committed independently. You may consider the use of a
            dedicated temporary cursor to do some database operation.
        """
        self._event_handlers[event].append(func)

    def _pop_event_handlers(self):
        # return the current handlers, and reset them on self
        result = self._event_handlers
        self._event_handlers = {'commit': [], 'rollback': []}
        return result

    @check
    def commit(self):
        """ Perform an SQL `COMMIT`
        """
        result = self._cnx.commit()
        for func in self._pop_event_handlers()['commit']:
            func()
        return result

    @check
    def rollback(self):
        """ Perform an SQL `ROLLBACK`
        """
        result = self._cnx.rollback()
        for func in self._pop_event_handlers()['rollback']:
            func()
        return result

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
        if exc_type is None:
            self.commit()
        self.close()

    @contextmanager
    @check
    def savepoint(self):
        """context manager entering in a new savepoint"""
        name = uuid.uuid1().hex
        self.execute('SAVEPOINT "%s"' % name)
        try:
            yield
        except Exception:
            self.execute('ROLLBACK TO SAVEPOINT "%s"' % name)
            raise
        else:
            self.execute('RELEASE SAVEPOINT "%s"' % name)

    @check
    def __getattr__(self, name):
        return getattr(self._obj, name)

    @property
    def closed(self):
        return self._closed

class TestCursor(Cursor):
    """ A cursor to be used for tests. It keeps the transaction open across
        several requests, and simulates committing, rolling back, and closing.
    """
    def __init__(self, *args, **kwargs):
        super(TestCursor, self).__init__(*args, **kwargs)
        # in order to simulate commit and rollback, the cursor maintains a
        # savepoint at its last commit
        self.execute("SAVEPOINT test_cursor")
        # we use a lock to serialize concurrent requests
        self._lock = threading.RLock()

    def acquire(self):
        self._lock.acquire()

    def release(self):
        self._lock.release()

    def force_close(self):
        super(TestCursor, self).close()

    def close(self):
        if not self._closed:
            self.rollback()             # for stuff that has not been committed
        self.release()

    def autocommit(self, on):
        _logger.debug("TestCursor.autocommit(%r) does nothing", on)

    def commit(self):
        self.execute("RELEASE SAVEPOINT test_cursor")
        self.execute("SAVEPOINT test_cursor")

    def rollback(self):
        self.execute("ROLLBACK TO SAVEPOINT test_cursor")
        self.execute("SAVEPOINT test_cursor")

class LazyCursor(object):
    """ A proxy object to a cursor. The cursor itself is allocated only if it is
        needed. This class is useful for cached methods, that use the cursor
        only in the case of a cache miss.
    """
    def __init__(self, dbname=None):
        self._dbname = dbname
        self._cursor = None
        self._depth = 0

    @property
    def dbname(self):
        return self._dbname or threading.currentThread().dbname

    def __getattr__(self, name):
        cr = self._cursor
        if cr is None:
            from odoo import registry
            cr = self._cursor = registry(self.dbname).cursor()
            for _ in xrange(self._depth):
                cr.__enter__()
        return getattr(cr, name)

    def __enter__(self):
        self._depth += 1
        if self._cursor is not None:
            self._cursor.__enter__()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self._depth -= 1
        if self._cursor is not None:
            self._cursor.__exit__(exc_type, exc_value, traceback)

class PsycoConnection(psycopg2.extensions.connection):
    pass

class ConnectionPool(object):
    """ The pool of connections to database(s)

        Keep a set of connections to pg databases open, and reuse them
        to open cursors for all transactions.

        The connections are *not* automatically closed. Only a close_db()
        can trigger that.
    """

    def locked(fun):
        @wraps(fun)
        def _locked(self, *args, **kwargs):
            self._lock.acquire()
            try:
                return fun(self, *args, **kwargs)
            finally:
                self._lock.release()
        return _locked

    def __init__(self, maxconn=64):
        self._connections = []
        self._maxconn = max(maxconn, 1)
        self._lock = threading.Lock()

    def __repr__(self):
        used = len([1 for c, u in self._connections[:] if u])
        count = len(self._connections)
        return "ConnectionPool(used=%d/count=%d/max=%d)" % (used, count, self._maxconn)

    def _debug(self, msg, *args):
        _logger.debug(('%r ' + msg), self, *args)

    @locked
    def borrow(self, connection_info):
        """
        :param dict connection_info: dict of psql connection keywords
        :rtype: PsycoConnection
        """
        # free dead and leaked connections
        for i, (cnx, _) in tools.reverse_enumerate(self._connections):
            if cnx.closed:
                self._connections.pop(i)
                self._debug('Removing closed connection at index %d: %r', i, cnx.dsn)
                continue
            if getattr(cnx, 'leaked', False):
                delattr(cnx, 'leaked')
                self._connections.pop(i)
                self._connections.append((cnx, False))
                _logger.info('%r: Free leaked connection to %r', self, cnx.dsn)

        for i, (cnx, used) in enumerate(self._connections):
            if not used and cnx._original_dsn == connection_info:
                try:
                    cnx.reset()
                except psycopg2.OperationalError:
                    self._debug('Cannot reset connection at index %d: %r', i, cnx.dsn)
                    # psycopg2 2.4.4 and earlier do not allow closing a closed connection
                    if not cnx.closed:
                        cnx.close()
                    continue
                self._connections.pop(i)
                self._connections.append((cnx, True))
                self._debug('Borrow existing connection to %r at index %d', cnx.dsn, i)

                return cnx

        if len(self._connections) >= self._maxconn:
            # try to remove the oldest connection not used
            for i, (cnx, used) in enumerate(self._connections):
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
        result._original_dsn = connection_info
        self._connections.append((result, True))
        self._debug('Create new connection')
        return result

    @locked
    def give_back(self, connection, keep_in_pool=True):
        self._debug('Give back connection to %r', connection.dsn)
        for i, (cnx, used) in enumerate(self._connections):
            if cnx is connection:
                self._connections.pop(i)
                if keep_in_pool:
                    self._connections.append((cnx, False))
                    self._debug('Put connection to %r in pool', cnx.dsn)
                else:
                    self._debug('Forgot connection to %r', cnx.dsn)
                    cnx.close()
                break
        else:
            raise PoolError('This connection does not below to the pool')

    @locked
    def close_all(self, dsn=None):
        count = 0
        last = None
        for i, (cnx, used) in tools.reverse_enumerate(self._connections):
            if dsn is None or cnx._original_dsn == dsn:
                cnx.close()
                last = self._connections.pop(i)[0]
                count += 1
        _logger.info('%r: Closed %d connections %s', self, count,
                    (dsn and last and 'to %r' % last.dsn) or '')


class Connection(object):
    """ A lightweight instance of a connection to postgres
    """
    def __init__(self, pool, dbname, dsn):
        self.dbname = dbname
        self.dsn = dsn
        self.__pool = pool

    def cursor(self, serialized=True):
        cursor_type = serialized and 'serialized ' or ''
        _logger.debug('create %scursor to %r', cursor_type, self.dsn)
        return Cursor(self.__pool, self.dbname, self.dsn, serialized=serialized)

    def test_cursor(self, serialized=True):
        cursor_type = serialized and 'serialized ' or ''
        _logger.debug('create test %scursor to %r', cursor_type, self.dsn)
        return TestCursor(self.__pool, self.dbname, self.dsn, serialized=serialized)

    # serialized_cursor is deprecated - cursors are serialized by default
    serialized_cursor = cursor

    def __nonzero__(self):
        """Check if connection is possible"""
        try:
            _logger.info("__nonzero__() is deprecated. (It is too expensive to test a connection.)")
            cr = self.cursor()
            cr.close()
            return True
        except Exception:
            return False

def connection_info_for(db_or_uri):
    """ parse the given `db_or_uri` and return a 2-tuple (dbname, connection_params)

    Connection params are either a dictionary with a single key ``dsn``
    containing a connection URI, or a dictionary containing connection
    parameter keywords which psycopg2 can build a key/value connection string
    (dsn) from

    :param str db_or_uri: database name or postgres dsn
    :rtype: (str, dict)
    """
    if db_or_uri.startswith(('postgresql://', 'postgres://')):
        # extract db from uri
        us = urlparse.urlsplit(db_or_uri)
        if len(us.path) > 1:
            db_name = us.path[1:]
        elif us.username:
            db_name = us.username
        else:
            db_name = us.hostname
        return db_name, {'dsn': db_or_uri}

    connection_info = {'database': db_or_uri}
    for p in ('host', 'port', 'user', 'password'):
        cfg = tools.config['db_' + p]
        if cfg:
            connection_info[p] = cfg

    return db_or_uri, connection_info

_Pool = None

def db_connect(to, allow_uri=False):
    global _Pool
    if _Pool is None:
        _Pool = ConnectionPool(int(tools.config['db_maxconn']))

    db, info = connection_info_for(to)
    if not allow_uri and db != to:
        raise ValueError('URI connections not allowed')
    return Connection(_Pool, db, info)

def close_db(db_name):
    """ You might want to call odoo.modules.registry.Registry.delete(db_name) along this function."""
    global _Pool
    if _Pool:
        _Pool.close_all(connection_info_for(db_name)[1])

def close_all():
    global _Pool
    if _Pool:
        _Pool.close_all()
