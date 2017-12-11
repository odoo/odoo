# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, users


class TestMailPerformance(TransactionCase):

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

    @users('admin', 'demo')
    def test_read_mail(self):
        """ Read records inheriting from 'mail.thread'. """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        # warm up ormcache
        records.mapped('partner_id.country_id.name')
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=3, demo=3):
            # without cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # with cache
            for record in records:
                record.partner_id.country_id.name

        with self.assertQueryCount(0):
            # value_pc must have been prefetched, too
            for record in records:
                record.value_pc

    @users('admin', 'demo')
    def test_write_mail(self):
        """ Write records inheriting from 'mail.thread' (no recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        # warm up ormcache
        records.write({'name': 'X'})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=4, demo=4):
            records.write({'name': 'Y'})

    @users('admin', 'demo')
    def test_write_mail_with_recomputation(self):
        """ Write records inheriting from 'mail.thread' (with recomputation). """
        records = self.env['test_performance.mail'].search([])
        self.assertEqual(len(records), 5)

        # warm up ormcache
        records.write({'value': 21})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=6, demo=6):
            records.write({'value': 42})

    @users('admin', 'demo')
    def test_write_mail_with_tracking(self):
        """ Write records inheriting from 'mail.thread' (with field tracking). """
        record = self.env['test_performance.mail'].search([], limit=1)
        self.assertEqual(len(record), 1)

        # warm up ormcache
        record.track = 'X'
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=20, demo=31):
            record.track = 'Y'

    @users('admin', 'demo')
    def test_create_mail(self):
        """ Create records inheriting from 'mail.thread' (without field tracking). """
        model = self.env['test_performance.mail']

        # warm up ormcache
        model.with_context(tracking_disable=True).create({'name': 'X'})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=3, demo=3):
            model.with_context(tracking_disable=True).create({'name': 'Y'})

    @users('admin', 'demo')
    def test_create_mail_with_tracking(self):
        """ Create records inheriting from 'mail.thread' (with field tracking). """
        model = self.env['test_performance.mail']

        # warm up ormcache
        model.create({'name': 'X'})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=38, demo=54):
            model.create({'name': 'Y'})

    @users('admin', 'emp')
    def test_simple(self):
        """ Create records inheriting from 'mail.thread' (simple models) """
        model = self.env['mail.test.simple']

        # warm up ormcache
        model.create({'name': 'Warm up'})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=22, emp=29):
            model.create({'name': 'Test'})


class TestAdvMailPerformance(TransactionCase):

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

    @users('admin', 'emp')
    def test_activity(self):
        model = self.env['mail.test.activity']

        # warm up ormcache
        model.create({'name': 'Test 0'})
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=25, emp=32):
            model.create({'name': 'Test'})

    @users('admin', 'emp')
    def test_activity_full(self):
        record = self.env['mail.test.activity'].create({'name': 'Test'})
        model = self.env['mail.activity'].with_context({
            'default_res_model': 'mail.test.activity',
        })

        # warm up ormcache
        model.create({
            'summary': 'Test Activity 0',
            'res_id': record.id,
        })
        self.env.cache.invalidate()

        with self.assertQueryCount(admin=46, emp=51):
            model.create({
                'summary': 'Test Activity',
                'res_id': record.id,
            })
