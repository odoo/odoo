# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from functools import partial

import odoo
from odoo.sql_db import TestCursor
from odoo.tests import common
from odoo.tests.common import BaseCase
from odoo.tools.misc import mute_logger

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
