# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, users, warmup
from odoo.tests import tagged
from odoo.tools import mute_logger


@tagged('performance')
class TestNewApiPerformance(TransactionCase):

    def setUp(self):
        super(TestNewApiPerformance, self).setUp()
        self._quick_create_ctx = {'no_reset_password': True}
        self.customer = self.env['res.partner'].create({
            'name': 'Customer',
            'email': 'customer.test@example.com',
        })

        self.user_employee = self.env['res.users'].with_context(self._quick_create_ctx).create({
            'name': 'Ernest Employee',
            'login': 'employee',
            'email': 'e.e@example.com',
            'groups_id': [(6, 0, [self.env.ref('base.group_user').id, self.env.ref('base.group_partner_manager').id])],
        })

    @users('__system__', 'employee')
    @warmup
    def test_create_compute_onchange_default(self):
        with self.assertQueryCount(__system__=2, employee=2):
            record = self.env['test_new_api.compute.onchange.default'].create({
                'name': 'Test',
            })
        self.assertEqual(record.partner_id, self.env.user.partner_id)
        self.assertEqual(record.email, self.env.user.email_formatted)

    @users('__system__', 'employee')
    @warmup
    def test_create_compute_onchange_default_onchange(self):
        with self.assertQueryCount(__system__=2, employee=2):
            record = self.env['test_new_api.compute.onchange.default'].with_context({
                'default_template_partner_id': self.customer.id
            }).create({
                'name': 'Test',
            })
        self.assertEqual(record.partner_id, self.customer)
        self.assertEqual(record.email, self.customer.email_formatted)

    @users('__system__', 'employee')
    @warmup
    def test_create_compute_onchange_default_specified(self):
        with self.assertQueryCount(__system__=2, employee=2):
            record = self.env['test_new_api.compute.onchange.default'].with_context({
                'default_partner_id': self.customer.id
            }).create({
                'name': 'Test',
            })
        self.assertEqual(record.partner_id, self.customer)
        self.assertEqual(record.email, self.customer.email_formatted)

    @users('__system__', 'employee')
    @warmup
    def test_write_compute_onchange_default(self):
        """ Read records inheriting from 'mail.thread'. """
        record = self.env['test_new_api.compute.onchange.default'].create({
            'name': 'Test',
        })
        self.assertEqual(record.partner_id, self.env.user.partner_id)
        self.assertEqual(record.email, self.env.user.email_formatted)

        with self.assertQueryCount(__system__=2, employee=2):
            record.update({'partner_id': self.customer.id})
            record._onchange_partner_id()

        self.assertEqual(record.partner_id, self.customer)
        self.assertEqual(record.email, self.customer.email_formatted)

    @users('__system__', 'employee')
    @warmup
    def test_write_compute_onchange_default_specified(self):
        """ Read records inheriting from 'mail.thread'. """
        record = self.env['test_new_api.compute.onchange.default'].create({
            'name': 'Test',
        })
        self.assertEqual(record.partner_id, self.env.user.partner_id)
        self.assertEqual(record.email, self.env.user.email_formatted)

        with self.assertQueryCount(__system__=2, employee=2):
            record.update({'template_partner_id': self.customer.id})
            record._onchange_template_partner_id()
            record._onchange_partner_id()

        self.assertEqual(record.partner_id, self.customer)
        self.assertEqual(record.email, self.customer.email_formatted)
