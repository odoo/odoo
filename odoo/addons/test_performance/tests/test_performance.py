# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from contextlib import contextmanager
import logging

from odoo.tests.common import TransactionCase

sql_logger = logging.getLogger('odoo.sql_db')


class TestPerformance(TransactionCase):
    @contextmanager
    def assertMaxQueries(self, message, count):
        """ Check the number of queries made in this scope. """
        count0 = self.cr.sql_log_count
        yield
        count1 = self.cr.sql_log_count
        self.assertLessEqual(count1 - count0, count, message)

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

    def test_read_base(self):
        """ Check reading records. """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        # without cache
        with self.assertMaxQueries("Prefetch records", 3):
            for record in records:
                record.partner_id.country_id.name

        # with cache
        with self.assertMaxQueries("Read prefetched records", 0):
            for record in records:
                record.partner_id.country_id.name

        # value_pc must have been prefetched, too
        with self.assertMaxQueries("Read another field on prefetched records", 0):
            for record in records:
                record.value_pc

    def test_read_mail(self):
        """ Check reading records inheriting from 'mail.thread'. """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        # without cache
        with self.assertMaxQueries("Prefetch records", 3):
            for record in records:
                record.partner_id.country_id.name

        # with cache
        with self.assertMaxQueries("Read prefetched records", 0):
            for record in records:
                record.partner_id.country_id.name

        # value_pc must have been prefetched, too
        with self.assertMaxQueries("Read another field on prefetched records", 0):
            for record in records:
                record.value_pc

    def test_write_base(self):
        """ Check writing records. """
        records = self.env['test_performance.base'].search([])
        self.assertEqual(len(records), 5)

        # warm up the caches
        records.write({'name': 'Start', 'value': 10})

        # write in batch, without recomputation
        with self.assertMaxQueries("Write in batch, no recomputation", 1):
            records.write({'name': 'X'})

        # write one by one, without recomputation
        with self.assertMaxQueries("Write one by one, no recomputation", 5):
            for record in records:
                record.name = 'Y'

        # write in batch, with recomputation
        with self.assertMaxQueries("Write in batch, with recomputation", 3):
            records.write({'value': 20})

        # write one by one, with recomputation
        with self.assertMaxQueries("Write one by one, with recomputation", 15):
            for record in records:
                record.value = 30

    def test_write_mail(self):
        """ Check writing records inheriting from 'mail.thread'. """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        # warm up the caches
        records.write({'value': 0})
        records.write({'name': '0'})

        # write in batch, without recomputation
        with self.assertMaxQueries("Write in batch, no recomputation", 3):
            records.write({'name': 'X'})

        # write one by one, without recomputation
        with self.assertMaxQueries("Write one by one, no recomputation", 15):
            for record in records:
                record.name = 'Y'

        # write in batch, with recomputation
        with self.assertMaxQueries("Write in batch, with recomputation", 5):
            records.write({'value': 20})

        # write one by one, with recomputation
        with self.assertMaxQueries("Write one by one, with recomputation", 25):
            for record in records:
                record.value = 30

        # write on a tracked field
        with self.assertMaxQueries("Write on a tracked field", 48):
            records[0].track = 'X'

    def test_create_base(self):
        """ Check creating records. """
        model = self.env['test_performance.base']

        # warm up caches
        model.create({'name': 'X'})

        # create record without lines
        with self.assertMaxQueries("Create record without lines", 6):
            model.create({'name': 'X'})

        # create record with lines
        with self.assertMaxQueries("Create record with lines", 39):
            model.create({
                'name': 'X',
                'line_ids': [(0, 0, {'value': val}) for val in range(10)],
            })

    def test_create_mail(self):
        """ Check creating records inheriting from 'mail.thread'. """
        model = self.env['test_performance.mail']

        # warm up caches
        model.create({'name': 'X'})

        # create without tracking changes
        with self.assertMaxQueries("Create record without tracking fields", 3):
            model.with_context(tracking_disable=True).create({'name': 'X'})

        # create with tracking changes
        with self.assertMaxQueries("Create record with tracking fields", 87):
            model.create({'name': 'X'})
