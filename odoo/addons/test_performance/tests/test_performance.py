# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
import functools
import logging

from odoo.tests.common import TransactionCase

_logger = logging.getLogger(__name__)
sql_logger = logging.getLogger('odoo.sql_db')


def queryCount(**counters):
    """ Decorate a method to check the number of queries it makes. Counters
    is a dict { 'user_login': expected_query_count } """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self):
            if hasattr(self, 'test_users'):
                users = self.test_users.filtered(lambda user: user.login in counters.keys())
            else:
                users = self.env['res.users'].search([('login', 'in', list(counters.keys()))])
            for user in users:
                # switch user
                self.uid = user.id
                self.env = self.env(user=self.uid)
                # warm up the caches
                self._round = False
                func(self)
                self.env.cache.invalidate()
                # test for real, and check query count
                self._round = True
                self.resetQueryCount()
                func(self)
                self.resumeQueryCount()
                self.assertQueryCount(self.cr.sql_log_count - (self._count + self._count_halted),
                                      counters[user.login], user.login)

        return wrapper

    return decorate


class TestPerformance(TransactionCase):

    def setUp(self):
        super(TestPerformance, self).setUp()
        self._round = False
        self._count = 0
        self._halted = False
        self._count_halted_start = 0
        self._count_halted = 0

    def assertQueryCount(self, actual, expected, message):
        self.assertLessEqual(actual, expected, message)
        if actual < expected:
            _logger.info("Warning: Got %d queries instead of %d: %s", actual, expected, message)

    def resetQueryCount(self):
        """ Reset the query counter. """
        self._count = self.cr.sql_log_count

    def haltQueryCount(self):
        """ Halt the query counter. """
        self._halted = True
        self._count_halted_start = self.cr.sql_log_count

    def resumeQueryCount(self):
        """ Resume query counter """
        if self._halted:
            self._count_halted += self.cr.sql_log_count - self._count_halted_start
            self._halted = False

    def str(self, value):
        """ Return a value different from run to run. """
        return value + 'z' if self._round else value

    def int(self, value):
        """ Return a value different from run to run. """
        return value + 1 if self._round else value

    @contextmanager
    def logQueries(self):
        """ Log the queries that are made in this scope. """
        sql_log, level = self.cr.sql_log, sql_logger.getEffectiveLevel()
        try:
            sql_logger.setLevel(logging.DEBUG)
            self.cr.sql_log = True
            yield
        finally:
            self.cr.sql_log = sql_log
            sql_logger.setLevel(level)


class TestBasePerformance(TestPerformance):

    @queryCount(admin=3, demo=3)
    def test_read_base(self):
        """ Read records. """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        # without cache
        for record in records:
            record.partner_id.country_id.name

        # with cache
        for record in records:
            record.partner_id.country_id.name

        # value_pc must have been prefetched, too
        for record in records:
            record.value_pc

    @queryCount(admin=1, demo=1)
    def test_write_base(self):
        """ Write records (no recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'name': self.str('X')})

    @queryCount(admin=3, demo=3)
    def test_write_base_with_recomputation(self):
        """ Write records (with recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'value': self.int(20)})

    @queryCount(admin=6, demo=6)
    def test_create_base(self):
        """ Create records. """
        model = self.env['test_performance.base']
        model.create({'name': self.str('X')})

    @queryCount(admin=38, demo=38)
    def test_create_base_with_lines(self):
        """ Create records with one2many lines. """
        model = self.env['test_performance.base']
        model.create({
            'name': self.str('Y'),
            'line_ids': [(0, 0, {'value': val}) for val in range(10)],
        })

    @queryCount(admin=17, demo=17)
    def test_create_base_with_tags(self):
        """ Create records with many2many tags. """
        model = self.env['test_performance.base']
        model.create({
            'name': self.str('X'),
            'tag_ids': [(0, 0, {'name': val}) for val in range(10)],
        })
