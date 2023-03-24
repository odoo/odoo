# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
from functools import partial

import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_REPEATABLE_READ

import odoo
from odoo.sql_db import db_connect, TestCursor
from odoo.tests import common
from odoo.tests.common import BaseCase
from odoo.tools.misc import config

ADMIN_USER_ID = common.ADMIN_USER_ID

def registry():
    return odoo.registry(common.get_db_name())


class TestRealCursor(BaseCase):

    def test_execute_bad_params(self):
        """
        Try to use iterable but non-list or int params in query parameters.
        """
        with registry().cursor() as cr:
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE login=%s", 'admin')
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", 1)
            with self.assertRaises(ValueError):
                cr.execute("SELECT id FROM res_users WHERE id=%s", '1')

    def test_using_closed_cursor(self):
        with registry().cursor() as cr:
            cr.close()
            with self.assertRaises(psycopg2.InterfaceError):
                cr.execute("SELECT 1")

    def test_multiple_close_call_cursor(self):
        cr = registry().cursor()
        cr.close()
        cr.close()

    def test_transaction_isolation_cursor(self):
        with registry().cursor() as cr:
            self.assertEqual(cr.connection.isolation_level, ISOLATION_LEVEL_REPEATABLE_READ)

class TestTestCursor(common.TransactionCase):
    def setUp(self):
        super().setUp()
        # make the registry in test mode
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)
        # now we make a test cursor for self.cr
        self.cr = self.registry.cursor()
        self.addCleanup(self.cr.close)
        self.env = odoo.api.Environment(self.cr, odoo.SUPERUSER_ID, {})
        self.record = self.env['res.partner'].create({'name': 'Foo'})

    def write(self, record, value):
        record.ref = value

    def flush(self, record):
        record.flush_model(['ref'])

    def check(self, record, value):
        # make sure to fetch the field from the database
        record.invalidate_recordset()
        self.assertEqual(record.read(['ref'])[0]['ref'], value)

    def test_single_cursor(self):
        """ Check the behavior of a single test cursor. """
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, 'A')
        self.cr.commit()

        self.write(self.record, 'B')
        self.cr.rollback()
        self.check(self.record, 'A')

        self.write(self.record, 'C')
        self.cr.rollback()
        self.check(self.record, 'A')

    def test_sub_commit(self):
        """ Check the behavior of a subcursor that commits. """
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, 'A')
        self.cr.commit()

        self.write(self.record, 'B')
        self.flush(self.record)

        # check behavior of a "sub-cursor" that commits
        with self.registry.cursor() as cr:
            self.assertIsInstance(cr, TestCursor)
            record = self.record.with_env(self.env(cr=cr))
            self.check(record, 'B')
            self.write(record, 'C')

        self.check(self.record, 'C')

        self.cr.rollback()
        self.check(self.record, 'A')

    def test_sub_rollback(self):
        """ Check the behavior of a subcursor that rollbacks. """
        self.assertIsInstance(self.cr, TestCursor)
        self.write(self.record, 'A')
        self.cr.commit()

        self.write(self.record, 'B')
        self.flush(self.record)

        # check behavior of a "sub-cursor" that rollbacks
        with self.assertRaises(ValueError):
            with self.registry.cursor() as cr:
                self.assertIsInstance(cr, TestCursor)
                record = self.record.with_env(self.env(cr=cr))
                self.check(record, 'B')
                self.write(record, 'C')
                raise ValueError(42)

        self.check(self.record, 'B')

        self.cr.rollback()
        self.check(self.record, 'A')

    def test_interleaving(self):
        """If test cursors are retrieved independently it becomes possible for
        the savepoint operations to be interleaved (especially as some are lazy
        e.g. the request cursor, so cursors might be semantically nested but
        technically interleaved), and for them to commit one another:

        .. code-block:: sql

            SAVEPOINT A
            SAVEPOINT B
            RELEASE SAVEPOINT A
            RELEASE SAVEPOINT B -- "savepoint b does not exist"
        """
        a = self.registry.cursor()
        _b = self.registry.cursor()
        # `a` should warn that it found un-closed cursor `b` when trying to close itself
        with self.assertLogs('odoo.sql_db', level=logging.WARNING) as cm:
            a.close()
        [msg] = cm.output
        self.assertIn('WARNING:odoo.sql_db:Found different un-closed cursor', msg)
        # avoid a warning on teardown (when self.cr finds a still on the stack)
        # as well as ensure the stack matches our expectations
        self.assertEqual(a._cursors_stack.pop(), a)

    def test_borrow_connection(self):
        """Tests the behavior of the postgresql connection pool recycling/borrowing"""
        origin_db_port = config['db_port']
        if not origin_db_port and hasattr(self.env.cr._cnx, 'info'):
            # Check the edge case of the db port set,
            # which is set as an integer in our DSN/connection_info
            # but as string in the DSN of psycopg2
            # The connections must be recycled/borrowed when the db_port is set
            # e.g
            # `connection.dsn`
            # {'database': '14.0', 'port': 5432, 'sslmode': 'prefer'}
            # must match
            # `cr._cnx.dsn`
            # 'port=5432 sslmode=prefer dbname=14.0'
            config['db_port'] = self.env.cr._cnx.info.port

        cursors = []
        try:
            connection = db_connect(self.cr.dbname)

            # Case #1: 2 cursors, both opened/used, do not recycle/borrow.
            # The 2nd cursor must not use the connection of the 1st cursor as it's used (not closed).
            cursors.append(connection.cursor())
            cursors.append(connection.cursor())
            # Ensure the port is within psycopg's dsn, as explained in an above comment,
            # we want to test the behavior of the connections borrowing including the port provided in the dsn.
            if config['db_port']:
                self.assertTrue('port=' in cursors[0]._cnx.dsn)
            # Check the connection of the 1st cursor is different than the connection of the 2nd cursor.
            self.assertNotEqual(id(cursors[0]._cnx), id(cursors[1]._cnx))

            # Case #2: Close 1st cursor, open 3rd cursor, must recycle/borrow.
            # The 3rd must recycle/borrow the connection of the 1st one.
            cursors[0].close()
            cursors.append(connection.cursor())
            # Check the connection of this 3rd cursor uses the connection of the 1st cursor that has been closed.
            self.assertEqual(id(cursors[0]._cnx), id(cursors[2]._cnx))

        finally:
            # Cleanups:
            # - Close the cursors which have been left opened
            # - Reset the config `db_port`
            for cursor in cursors:
                if not cursor.closed:
                    cursor.close()
            config['db_port'] = origin_db_port


class TestCursorHooks(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.log = []

    def prepare_hooks(self, cr):
        self.log.clear()
        cr.precommit.add(partial(self.log.append, 'preC'))
        cr.postcommit.add(partial(self.log.append, 'postC'))
        cr.prerollback.add(partial(self.log.append, 'preR'))
        cr.postrollback.add(partial(self.log.append, 'postR'))
        self.assertEqual(self.log, [])

    def test_hooks_on_cursor(self):
        cr = self.registry.cursor()

        # check hook on commit()
        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ['preC', 'postC'])

        # check hook on flush(), then on rollback()
        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ['preC'])
        cr.rollback()
        self.assertEqual(self.log, ['preC', 'preR', 'postR'])

        # check hook on close()
        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ['preR', 'postR'])

    def test_hooks_on_testcursor(self):
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)

        cr = self.registry.cursor()

        # check hook on commit(); post-commit hooks are ignored
        self.prepare_hooks(cr)
        cr.commit()
        self.assertEqual(self.log, ['preC'])

        # check hook on flush(), then on rollback()
        self.prepare_hooks(cr)
        cr.flush()
        self.assertEqual(self.log, ['preC'])
        cr.rollback()
        self.assertEqual(self.log, ['preC', 'preR', 'postR'])

        # check hook on close()
        self.prepare_hooks(cr)
        cr.close()
        self.assertEqual(self.log, ['preR', 'postR'])
