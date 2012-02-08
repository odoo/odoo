# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>).
#    Copyright (C) 2010-2011 OpenERP s.a. (<http://openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

#.apidoc title: PostgreSQL interface

"""
The PostgreSQL connector is a connectivity layer between the OpenERP code and
the database, *not* a database abstraction toolkit. Database abstraction is what
the ORM does, in fact.

See also: the `pooler` module
"""

#.apidoc add-functions: print_stats
#.apidoc add-classes: Cursor Connection ConnectionPool

__all__ = ['db_connect', 'close_db']

from functools import wraps
import logging
import psycopg2.extensions
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_READ_COMMITTED, ISOLATION_LEVEL_REPEATABLE_READ
from psycopg2.pool import PoolError
from psycopg2.psycopg1 import cursor as psycopg1cursor
from threading import currentThread

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

_logger = logging.getLogger(__name__)

types_mapping = {
    'date': (1082,),
    'time': (1083,),
    'datetime': (1114,),
}

def unbuffer(symb, cr):
    if symb is None: return None
    return str(symb)

def undecimalize(symb, cr):
    if symb is None: return None
    return float(symb)

for name, typeoid in types_mapping.items():
    psycopg2.extensions.register_type(psycopg2.extensions.new_type(typeoid, name, lambda x, cr: x))
psycopg2.extensions.register_type(psycopg2.extensions.new_type((700, 701, 1700,), 'float', undecimalize))


import tools
from tools.func import frame_codeinfo
from datetime import datetime as mdt
from datetime import timedelta
import threading
from inspect import currentframe

import re
re_from = re.compile('.* from "?([a-zA-Z_0-9]+)"? .*$');
re_into = re.compile('.* into "?([a-zA-Z_0-9]+)"? .*$');

sql_counter = 0

class Cursor(object):
    """Represents an open transaction to the PostgreSQL DB backend,
       acting as a lightweight wrapper around psycopg2's
       ``psycopg1cursor`` objects.

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

    """
    IN_MAX = 1000 # decent limit on size of IN queries - guideline = Oracle limit

    def check(f):
        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if self.__closed:
                msg = 'Unable to use a closed cursor.'
                if self.__closer:
                    msg += ' It was closed at %s, line %s' % self.__closer
                raise psycopg2.OperationalError(msg)
            return f(self, *args, **kwargs)
        return wrapper

    def __init__(self, pool, dbname, serialized=True):
        self.sql_from_log = {}
        self.sql_into_log = {}

        # default log level determined at cursor creation, could be
        # overridden later for debugging purposes
        self.sql_log = _logger.isEnabledFor(logging.DEBUG)

        self.sql_log_count = 0
        self.__closed = True    # avoid the call of close() (by __del__) if an exception
                                # is raised by any of the following initialisations
        self._pool = pool
        self.dbname = dbname

        # Whether to enable snapshot isolation level for this cursor.
        # see also the docstring of Cursor.  
        self._serialized = serialized

        self._cnx = pool.borrow(dsn(dbname))
        self._obj = self._cnx.cursor(cursor_factory=psycopg1cursor)
        if self.sql_log:
            self.__caller = frame_codeinfo(currentframe(),2)
        else:
            self.__caller = False
        self.__closed = False   # real initialisation value
        self.autocommit(False)
        self.__closer = False

        self._default_log_exceptions = True

    def __del__(self):
        if not self.__closed and not self._cnx.closed:
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
        if '%d' in query or '%f' in query:
            _logger.warning(query)
            _logger.warning("SQL queries cannot contain %d or %f anymore. "
                         "Use only %s")

        if self.sql_log:
            now = mdt.now()

        try:
            params = params or None
            res = self._obj.execute(query, params)
        except psycopg2.ProgrammingError, pe:
            if (self._default_log_exceptions if log_exceptions is None else log_exceptions):
                _logger.error("Programming error: %s, in query %s", pe, query)
            raise
        except Exception:
            if (self._default_log_exceptions if log_exceptions is None else log_exceptions):
                _logger.exception("bad query: %s", self._obj.query or query)
            raise

        if self.sql_log:
            delay = mdt.now() - now
            delay = delay.seconds * 1E6 + delay.microseconds

            _logger.debug("query: %s", self._obj.query)
            self.sql_log_count+=1
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


    def split_for_in_conditions(self, ids):
        """Split a list of identifiers into one or more smaller tuples
           safe for IN conditions, after uniquifying them."""
        return tools.misc.split_every(self.IN_MAX, set(ids))

    def print_log(self):
        global sql_counter
        sql_counter += self.sql_log_count
        if not self.sql_log:
            return
        def process(type):
            sqllogs = {'from':self.sql_from_log, 'into':self.sql_into_log}
            sum = 0
            if sqllogs[type]:
                sqllogitems = sqllogs[type].items()
                sqllogitems.sort(key=lambda k: k[1][1])
                _logger.debug("SQL LOG %s:", type)
                sqllogitems.sort(lambda x,y: cmp(x[1][0], y[1][0]))
                for r in sqllogitems:
                    delay = timedelta(microseconds=r[1][1])
                    _logger.debug("table: %s: %s/%s",
                                        r[0], delay, r[1][0])
                    sum+= r[1][1]
                sqllogs[type].clear()
            sum = timedelta(microseconds=sum)
            _logger.debug("SUM %s:%s/%d [%d]",
                                type, sum, self.sql_log_count, sql_counter)
            sqllogs[type].clear()
        process('from')
        process('into')
        self.sql_log_count = 0
        self.sql_log = False

    @check
    def close(self):
        return self._close(False)

    def _close(self, leak=False):
        if not self._obj:
            return

        if self.sql_log:
            self.__closer = frame_codeinfo(currentframe(),3)
        self.print_log()

        self._obj.close()

        # This force the cursor to be freed, and thus, available again. It is
        # important because otherwise we can overload the server very easily
        # because of a cursor shortage (because cursors are not garbage
        # collected as fast as they should). The problem is probably due in
        # part because browse records keep a reference to the cursor.
        del self._obj
        self.__closed = True

        # Clean the underlying connection.
        self._cnx.rollback()

        if leak:
            self._cnx.leaked = True
        else:
            chosen_template = tools.config['db_template']
            templates_list = tuple(set(['template0', 'template1', 'postgres', chosen_template]))
            keep_in_pool = self.dbname not in templates_list
            self._pool.give_back(self._cnx, keep_in_pool=keep_in_pool)

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
            isolation_level = ISOLATION_LEVEL_REPEATABLE_READ \
                                  if self._serialized \
                                  else ISOLATION_LEVEL_READ_COMMITTED
        self._cnx.set_isolation_level(isolation_level)

    @check
    def commit(self):
        """ Perform an SQL `COMMIT`
        """
        return self._cnx.commit()

    @check
    def rollback(self):
        """ Perform an SQL `ROLLBACK`
        """
        return self._cnx.rollback()

    @check
    def __getattr__(self, name):
        return getattr(self._obj, name)

        """ Set the mode of postgres operations for all cursors
        """
        """Obtain the mode of postgres operations for all cursors
        """

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
    def borrow(self, dsn):
        self._debug('Borrow connection to %r', dsn)

        # free leaked connections
        for i, (cnx, _) in tools.reverse_enumerate(self._connections):
            if cnx.closed:
                self._connections.pop(i)
                self._debug('Removing closed connection at index %d: %r', i, cnx.dsn)
                continue
            if getattr(cnx, 'leaked', False):
                delattr(cnx, 'leaked')
                self._connections.pop(i)
                self._connections.append((cnx, False))
                _logger.warning('%r: Free leaked connection to %r', self, cnx.dsn)

        for i, (cnx, used) in enumerate(self._connections):
            if not used and dsn_are_equals(cnx.dsn, dsn):
                self._connections.pop(i)
                self._connections.append((cnx, True))
                self._debug('Existing connection found at index %d', i)

                return cnx

        if len(self._connections) >= self._maxconn:
            # try to remove the oldest connection not used
            for i, (cnx, used) in enumerate(self._connections):
                if not used:
                    self._connections.pop(i)
                    self._debug('Removing old connection at index %d: %r', i, cnx.dsn)
                    break
            else:
                # note: this code is called only if the for loop has completed (no break)
                raise PoolError('The Connection Pool Is Full')

        try:
            result = psycopg2.connect(dsn=dsn, connection_factory=PsycoConnection)
        except psycopg2.Error:
            _logger.exception('Connection to the database failed')
            raise
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
    def close_all(self, dsn):
        _logger.info('%r: Close all connections to %r', self, dsn)
        for i, (cnx, used) in tools.reverse_enumerate(self._connections):
            if dsn_are_equals(cnx.dsn, dsn):
                cnx.close()
                self._connections.pop(i)


class Connection(object):
    """ A lightweight instance of a connection to postgres
    """

    def __init__(self, pool, dbname):
        self.dbname = dbname
        self._pool = pool

    def cursor(self, serialized=True):
        cursor_type = serialized and 'serialized ' or ''
        _logger.debug('create %scursor to %r', cursor_type, self.dbname)
        return Cursor(self._pool, self.dbname, serialized=serialized)

    # serialized_cursor is deprecated - cursors are serialized by default
    serialized_cursor = cursor

    def __nonzero__(self):
        """Check if connection is possible"""
        try:
            _logger.warning("__nonzero__() is deprecated. (It is too expensive to test a connection.)")
            cr = self.cursor()
            cr.close()
            return True
        except Exception:
            return False

def dsn(db_name):
    _dsn = ''
    for p in ('host', 'port', 'user', 'password'):
        cfg = tools.config['db_' + p]
        if cfg:
            _dsn += '%s=%s ' % (p, cfg)

    return '%sdbname=%s' % (_dsn, db_name)

def dsn_are_equals(first, second):
    def key(dsn):
        k = dict(x.split('=', 1) for x in dsn.strip().split())
        k.pop('password', None) # password is not relevant
        return k
    return key(first) == key(second)


_Pool = None

def db_connect(db_name):
    global _Pool
    if _Pool is None:
        _Pool = ConnectionPool(int(tools.config['db_maxconn']))
    currentThread().dbname = db_name
    return Connection(_Pool, db_name)

def close_db(db_name):
    global _Pool
    """ You might want to call openerp.modules.registry.RegistryManager.delete(db_name) along this function."""
    if _Pool:
        _Pool.close_all(dsn(db_name))
    ct = currentThread()
    if hasattr(ct, 'dbname'):
        delattr(ct, 'dbname')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

