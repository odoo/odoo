# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_performance.tests.test_performance import TestPerformance, queryCount


class TestMailPerformance(TestPerformance):

    @queryCount(admin=3, demo=3)
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

    @queryCount(admin=4, demo=4)
    def test_write_mail(self):
        """ Write records inheriting from 'mail.thread' (no recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'name': self.str('X')})

    @queryCount(admin=6, demo=6)
    def test_write_mail_with_recomputation(self):
        """ Write records inheriting from 'mail.thread' (with recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)
        self.resetQueryCount()

        records.write({'value': self.int(20)})

    @queryCount(admin=20, demo=31)
    def test_write_mail_with_tracking(self):
        """ Write records inheriting from 'mail.thread' (with field tracking). """
        record = self.env['test_performance.mail'].search([], limit=1)
        self.assertEqual(len(record), 1)
        self.resetQueryCount()

        record.track = self.str('X')

    @queryCount(admin=3, demo=3)
    def test_create_mail(self):
        """ Create records inheriting from 'mail.thread' (without field tracking). """
        model = self.env['test_performance.mail']
        model.with_context(tracking_disable=True).create({'name': self.str('X')})

    @queryCount(admin=38, demo=54)
    def test_create_mail_with_tracking(self):
        """ Create records inheriting from 'mail.thread' (with field tracking). """
        model = self.env['test_performance.mail']
        model.create({'name': self.str('Y')})
