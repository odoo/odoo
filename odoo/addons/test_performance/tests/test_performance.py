# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
import functools
import logging

from odoo.tests.common import TransactionCase

sql_logger = logging.getLogger('odoo.sql_db')


def queryCount(count):
    """ Decorate a method to check the number of queries it makes. """
    def decorate(func):
        @functools.wraps(func)
        def wrapper(self):
            # warm up the caches
            self._round = False
            func(self)
            self.env.cache.invalidate()
            # test for real, and check query count
            self._round = True
            self.resetQueryCount()
            func(self)
            self.assertLessEqual(self.cr.sql_log_count - self._count, count)

        return wrapper

    return decorate


class TestPerformance(TransactionCase):

    def resetQueryCount(self):
        """ Reset the query counter. """
        self._count = self.cr.sql_log_count

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

    @queryCount(3)
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

    @queryCount(3)
    def test_read_mail(self):
        """ Read records inheriting from 'mail.thread'. """
        records = self.env['test_performance.mail'].search([])
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

    @queryCount(1)
    def test_write_base(self):
        """ Write records (no recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'name': self.str('X')})

    @queryCount(3)
    def test_write_base_with_recomputation(self):
        """ Write records (with recomputation). """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'value': self.int(20)})

    @queryCount(7)
    def test_write_mail(self):
        """ Write records inheriting from 'mail.thread' (no recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'name': self.str('X')})

    @queryCount(9)
    def test_write_mail_with_recomputation(self):
        """ Write records inheriting from 'mail.thread' (with recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'value': self.int(20)})

    @queryCount(45)
    def test_write_mail_with_tracking(self):
        """ Write records inheriting from 'mail.thread' (with field tracking). """
        record = self.env['test_performance.mail'].search([], limit=1)
        self.assertEqual(len(record), 1)
        self.resetQueryCount()

        record.track = self.str('X')

    @queryCount(6)
    def test_create_base(self):
        """ Create records. """
        model = self.env['test_performance.base']
        model.create({'name': self.str('X')})

    @queryCount(38)
    def test_create_base_with_lines(self):
        """ Create records with lines. """
        model = self.env['test_performance.base']
        model.create({
            'name': self.str('Y'),
            'line_ids': [(0, 0, {'value': val}) for val in range(10)],
        })

    @queryCount(3)
    def test_create_mail(self):
        """ Create records inheriting from 'mail.thread' (without field tracking). """
        model = self.env['test_performance.mail']
        model.with_context(tracking_disable=True).create({'name': self.str('X')})

    @queryCount(87)
    def test_create_mail_with_tracking(self):
        """ Create records inheriting from 'mail.thread' (with field tracking). """
        model = self.env['test_performance.mail']
        model.create({'name': self.str('Y')})
