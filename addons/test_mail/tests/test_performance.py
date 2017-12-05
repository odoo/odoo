# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.test_performance.tests.test_performance import TestPerformance, queryCount


class TestMailPerformance(TestPerformance):

    def setUp(self):
        super(TestMailPerformance, self).setUp()
        self.user_employee = self.env['res.users'].with_context({
            'no_reset_password': True,
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }).create({
            'name': 'Ernest Employee',
            'login': 'emp',
            'email': 'e.e@example.com',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # for performances test
        self.admin = self.env.user
        self.admin.login = 'admin'

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

    @queryCount(admin=22, emp=29)
    def test_simple(self):
        """ Create records inheriting from 'mail.thread' (simple models) """
        self.env['mail.test.simple'].create({'name': self.str('Test')})


class TestAdvMailPerformance(TestPerformance):

    def setUp(self):
        super(TestAdvMailPerformance, self).setUp()
        self.user_employee = self.env['res.users'].with_context({
            'no_reset_password': True,
            'mail_create_nolog': True,
            'mail_create_nosubscribe': True,
            'mail_notrack': True,
        }).create({
            'name': 'Ernest Employee',
            'login': 'emp',
            'email': 'e.e@example.com',
            'signature': '--\nErnest',
            'notification_type': 'inbox',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id])],
        })

        # for performances test
        self.admin = self.env.user
        self.admin.login = 'admin'

    @queryCount(admin=25, emp=32)
    def test_activity(self):
        self.env['mail.test.activity'].create({'name': self.str('Test')})

    @queryCount(admin=45, emp=50)
    def test_activity_full(self):
        test_record_activity = self.env['mail.test.activity'].create({'name': self.str('Test')})
        res_id = test_record_activity.id
        self.resetQueryCount()

        self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        }).create({
            'summary': self.str('Test Activity'),
            'res_id': res_id,
        })
