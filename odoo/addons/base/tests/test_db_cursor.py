# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

import odoo
from odoo.sql_db import db_connect, TestCursor
from odoo.tests import common
from odoo.tests.common import BaseCase
from odoo.tools.misc import config, mute_logger

ADMIN_USER_ID = common.ADMIN_USER_ID

def registry():
    return odoo.registry(common.get_db_name())


class TestExecute(BaseCase):
    """ Try cr.execute with wrong parameters """

    @mute_logger('odoo.sql_db')
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


class TestTestCursor(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super(TestTestCursor, cls).setUpClass()
        r = registry()
        r.enter_test_mode(r.cursor())

    @classmethod
    def tearDownClass(cls):
        r = registry()
        r.test_cr.close()
        r.leave_test_mode()
        super(TestTestCursor, cls).tearDownClass()

    def setUp(self):
        super(TestTestCursor, self).setUp()
        self.record = self.env['res.partner'].create({'name': 'Foo'})

    def write(self, record, value):
        record.ref = value

    def flush(self, record):
        record.flush(['ref'])

    def check(self, record, value):
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

    def prepare_hooks(self, cr, precommit_msg, postcommit_msg, prerollback_msg, postrollback_msg):
        cr.precommit.add(partial(self.log.append, precommit_msg))
        cr.postcommit.add(partial(self.log.append, postcommit_msg))
        cr.prerollback.add(partial(self.log.append, prerollback_msg))
        cr.postrollback.add(partial(self.log.append, postrollback_msg))

    def test_hooks(self):
        cr = self.registry.cursor()

        # check hook on commit()
        self.prepare_hooks(cr, 'C1a', 'C1b', 'R1a', 'R1b')
        self.assertEqual(self.log, [])
        cr.commit()
        self.assertEqual(self.log, ['C1a', 'C1b'])

        # check hook on rollback()
        self.prepare_hooks(cr, 'C2a', 'C2b', 'R2a', 'R2b')
        self.assertEqual(self.log, ['C1a', 'C1b'])
        cr.rollback()
        self.assertEqual(self.log, ['C1a', 'C1b', 'R2a', 'R2b'])

        # check hook on close()
        self.prepare_hooks(cr, 'C3a', 'C3b', 'R3a', 'R3b')
        self.assertEqual(self.log, ['C1a', 'C1b', 'R2a', 'R2b'])
        cr.close()
        self.assertEqual(self.log, ['C1a', 'C1b', 'R2a', 'R2b', 'R3a', 'R3b'])

    def test_hooks_on_testcursor(self):
        self.registry.enter_test_mode(self.cr)
        self.addCleanup(self.registry.leave_test_mode)

        cr = self.registry.cursor()

        # check hook on commit(); post-commit hooks are ignored
        self.prepare_hooks(cr, 'C1a', 'C1b', 'R1a', 'R1b')
        self.assertEqual(self.log, [])
        cr.commit()
        self.assertEqual(self.log, ['C1a'])

        # check hook on rollback()
        self.prepare_hooks(cr, 'C2a', 'C2b', 'R2a', 'R2b')
        self.assertEqual(self.log, ['C1a'])
        cr.rollback()
        self.assertEqual(self.log, ['C1a', 'R2a', 'R2b'])

        # check hook on close()
        self.prepare_hooks(cr, 'C3a', 'C3b', 'R3a', 'R3b')
        self.assertEqual(self.log, ['C1a', 'R2a', 'R2b'])
        cr.close()
        self.assertEqual(self.log, ['C1a', 'R2a', 'R2b', 'R3a', 'R3b'])

class TestCursorHooksSavepointCaseCleanup(common.SavepointCase):
    """Check savepoint cases handle commit hooks properly."""
    def test_isolation_first(self):
        def mutate_second_test_ref():
            for name in ['precommit', 'postcommit', 'prerollback', 'postrollback']:
                del self.env.cr.precommit.data.get(f'test_cursor_hooks_savepoint_case_cleanup_test_second_{name}', [''])[0]
        self.env.cr.precommit.add(mutate_second_test_ref)

    def test_isolation_second(self):
        references = [['not_empty']]*4
        cr = self.env.cr
        commit_callbacks = [cr.precommit, cr.postcommit, cr.prerollback, cr.postrollback]
        callback_names = ['precommit', 'postcommit', 'prerollback', 'postrollback']

        for callback_name, callbacks, reference in zip(callback_names, commit_callbacks, references):
            callbacks.data.setdefault(f"test_cursor_hooks_savepoint_case_cleanup_test_second_{callback_name}", reference)

        for callback in commit_callbacks:
            callback.run()

        for callback_name, reference in zip(callback_names, references):
            self.assertTrue(bool(reference), f"{callback_name} failed to clean up between transaction tests")
            self.assertTrue(reference[0] == 'not_empty', f"{callback_name} failed to clean up between transaction tests")
