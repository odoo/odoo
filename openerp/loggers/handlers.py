##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2014 OpenERP SA (<http://www.openerp.com>)
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

import contextlib
import datetime
import logging
import threading

import psycopg2

from openerp import tools 

# The PostgreSQL Handler for the logging module, will be used by OpenERP to store the logs 
# in the database, --log-pgsql-database=YOUR_DBNAME
# By default the system will use the current database

class NoDatabaseError(Exception):
    pass

class PostgreSQLHandler(logging.Handler):
    @contextlib.contextmanager
    def create_connection(self):
        db_name = None

        db_name_from_cli = tools.config['log_pgsql_database']
        if not db_name_from_cli:
            # If there is no database, and only in this case, we are going to use the database 
            # from the current thread and create a connection to this database.

            current_thread = threading.current_thread()

            db_name_from_thread = getattr(current_thread, 'dbname', None)
            if isinstance(db_name_from_thread, basestring):
                db_name = db_name_from_thread
        else:
            db_name = db_name_from_cli

        if not db_name:
            raise NoDatabaseError("There is no defined database on this request")

        parameters = {
            'user': tools.config['db_user'] or None,
            'password': tools.config['db_password'] or None,
            'host': tools.config['db_host'] or None,
            'port': tools.config['db_port'] or None,
            'database': db_name,
        }
        try:
            connection = psycopg2.connect(**parameters)

            if connection:
                yield connection
        except Exception, ex:  # Use a specific exception
            print ex

    def _internal_emit(self, record):
        with self.create_connection() as conn:
            exception = False
            if record.exc_info:
                exception = record.exc_text

            now = datetime.datetime.utcnow()

            current_thread = threading.current_thread()
            uid = getattr(current_thread, 'uid', False)
            dbname = getattr(current_thread, 'dbname', False)

            parameters = (
                now, uid, now, uid, 'server', dbname, record.name,
                logging.getLevelName(record.levelno), record.msg, exception,
                record.filename, record.funcName, record.lineno
            )

            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO ir_logging(
                        create_date, create_uid, write_date, write_uid,
                        type, dbname, name, level, message, exception, path, func,
                        line
                    )
                    VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, parameters)
                conn.commit()

    def emit(self, record):
        # We use a context manager to be tolerant to the errors (error of connections,...)
        try:
            self._internal_emit(record)
        except NoDatabaseError:
            pass
