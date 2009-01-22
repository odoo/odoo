# -*- encoding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution	
#    Copyright (C) 2004-2009 Tiny SPRL (<http://tiny.be>). All Rights Reserved
#    $Id$
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import netsvc
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT, ISOLATION_LEVEL_SERIALIZABLE
from psycopg2.pool import ThreadedConnectionPool
from psycopg2.psycopg1 import cursor as psycopg1cursor

import psycopg2.extensions

psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)

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
import re

from mx import DateTime as mdt
re_from = re.compile('.* from "?([a-zA-Z_0-9]+)"? .*$');
re_into = re.compile('.* into "?([a-zA-Z_0-9]+)"? .*$');

def log(msg, lvl=netsvc.LOG_DEBUG):
    logger = netsvc.Logger()
    logger.notifyChannel('sql', lvl, msg)

sql_counter = 0

class Cursor(object):
    IN_MAX = 1000
    sql_from_log = {}
    sql_into_log = {}
    sql_log = False
    count = 0
    
    def check(f):
        from tools.func import wraps

        @wraps(f)
        def wrapper(self, *args, **kwargs):
            if not hasattr(self, '_obj'):
                raise psycopg2.ProgrammingError('Unable to use the cursor after having closed it')
            return f(self, *args, **kwargs)
        return wrapper

    def __init__(self, pool):
        self._pool = pool
        self._cnx = pool.getconn()
        self._obj = self._cnx.cursor(cursor_factory=psycopg1cursor)
        self.autocommit(False)
        self.dbname = pool.dbname

        if tools.config['log_level'] in (netsvc.LOG_DEBUG, netsvc.LOG_DEBUG_RPC):
            from inspect import stack
            self.__caller = tuple(stack()[2][1:3])
        
    def __del__(self):
        if hasattr(self, '_obj'):
            if tools.config['log_level'] in (netsvc.LOG_DEBUG, netsvc.LOG_DEBUG_RPC):
                # Oops. 'self' has not been closed explicitly.
                # The cursor will be deleted by the garbage collector, 
                # but the database connection is not put back into the connection
                # pool, preventing some operation on the database like dropping it.
                # This can also lead to a server overload.
                msg = "Cursor not closed explicitly\n"  \
                      "Cursor was created at %s:%s" % self.__caller

                log(msg, netsvc.LOG_WARNING)
            self.close()

    @check
    def execute(self, query, params=None):
        self.count+=1
        if '%d' in query or '%f' in query:
            log(query, netsvc.LOG_WARNING)
            log("SQL queries cannot contain %d or %f anymore. Use only %s", netsvc.LOG_WARNING)
            if params:
                query = query.replace('%d', '%s').replace('%f', '%s')

        if self.sql_log:
            now = mdt.now()
        
        try:
            res = self._obj.execute(query, params)
	except psycopg2.ProgrammingError, pe:
	    logger= netsvc.Logger()
	    logger.notifyChannel('sql_db', netsvc.LOG_ERROR, "Programming error: %s, in query %s" % (pe, query))
	    raise

        if self.sql_log:
            log("query: %s" % self._obj.query)
            self.count+=1
            res_from = re_from.match(query.lower())
            if res_from:
                self.sql_from_log.setdefault(res_from.group(1), [0, 0])
                self.sql_from_log[res_from.group(1)][0] += 1
                self.sql_from_log[res_from.group(1)][1] += mdt.now() - now
            res_into = re_into.match(query.lower())
            if res_into:
                self.sql_into_log.setdefault(res_into.group(1), [0, 0])
                self.sql_into_log[res_into.group(1)][0] += 1
                self.sql_into_log[res_into.group(1)][1] += mdt.now() - now
        return res

    def print_log(self):
	global sql_counter
	sql_counter += self.count
        def process(type):
            sqllogs = {'from':self.sql_from_log, 'into':self.sql_into_log}
            sum = 0
            if sqllogs[type]:
                sqllogitems = sqllogs[type].items()
                sqllogitems.sort(key=lambda k: k[1][1])
                log("SQL LOG %s:" % (type,))
                for r in sqllogitems:
                    log("table: %s: %s/%s" %(r[0], str(r[1][1]), r[1][0]))
                    sum+= r[1][1]
                sqllogs[type].clear()
            log("SUM:%s/%d [%d]" % (sum, self.count,sql_counter))
        process('from')
        process('into')
        self.count = 0
        self.sql_log = False

    @check
    def close(self):
        self.print_log()
        self._obj.close()

        # This force the cursor to be freed, and thus, available again. It is
        # important because otherwise we can overload the server very easily
        # because of a cursor shortage (because cursors are not garbage
        # collected as fast as they should). The problem is probably due in
        # part because browse records keep a reference to the cursor.
        del self._obj
        self._pool.putconn(self._cnx)
    
    @check
    def autocommit(self, on):
        self._cnx.set_isolation_level([ISOLATION_LEVEL_SERIALIZABLE, ISOLATION_LEVEL_AUTOCOMMIT][bool(on)])
    
    @check
    def commit(self):
        return self._cnx.commit()
    
    @check
    def rollback(self):
        return self._cnx.rollback()

    @check
    def __getattr__(self, name):
        return getattr(self._obj, name)

class ConnectionPool(object):
    def __init__(self, pool, dbname):
        self.dbname = dbname
        self._pool = pool

    def cursor(self):
        return Cursor(self)

    def __getattr__(self, name):
        return getattr(self._pool, name)

class PoolManager(object):
    _pools = {}
    _dsn = None
    maxconn =  int(tools.config['db_maxconn']) or 64
    
    @classmethod 
    def dsn(cls, db_name):
        if cls._dsn is None:
            cls._dsn = ''
            for p in ('host', 'port', 'user', 'password'):
                cfg = tools.config['db_' + p]
                if cfg:
                    cls._dsn += '%s=%s ' % (p, cfg)
        return '%s dbname=%s' % (cls._dsn, db_name)

    @classmethod
    def get(cls, db_name):
        if db_name not in cls._pools:
            logger = netsvc.Logger()
            try:
                logger.notifyChannel('dbpool', netsvc.LOG_INFO, 'Connecting to %s' % (db_name,))
                cls._pools[db_name] = ConnectionPool(ThreadedConnectionPool(1, cls.maxconn, cls.dsn(db_name)), db_name)
            except Exception, e:
                logger.notifyChannel('dbpool', netsvc.LOG_ERROR, 'Unable to connect to %s: %s' %
                                     (db_name, str(e)))
                raise
        return cls._pools[db_name]

    @classmethod
    def close(cls, db_name):
        if db_name in cls._pools:
            logger = netsvc.Logger()
            logger.notifyChannel('dbpool', netsvc.LOG_INFO, 'Closing all connections to %s' % (db_name,))
            cls._pools[db_name].closeall()
            del cls._pools[db_name]

def db_connect(db_name):
    return PoolManager.get(db_name)

def close_db(db_name):
    PoolManager.close(db_name)
    tools.cache.clean_caches_for_db(db_name)
    

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

