# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

import time
from odoo.addons.membership.tests.common import TestMembershipCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestMembership(TestMembershipCommon):

    def test_none_membership(self):
        self.membership_1.write({
            'membership_date_from': datetime.date.today() + relativedelta(years=-2),
            'membership_date_to': datetime.date.today() + relativedelta(years=-1),
        })

        self.partner_1.create_membership_invoice(self.membership_1, 75.0)
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: outdated non paid subscription should keep in non-member state')

    def test_old_membership(self):
        self.membership_1.write({
            'membership_date_from': datetime.date.today() + relativedelta(years=-2),
            'membership_date_to': datetime.date.today() + relativedelta(years=-1),
        })

        invoice = self.partner_1.create_membership_invoice(self.membership_1, 75.0)
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: outdated non paid subscription should keep in non-member state')

        # subscribes to a membership
        self.partner_1.create_membership_invoice(self.membership_1, 75.0)

        # checks for invoices
        self.assertEqual(
            invoice.state, 'draft',
            'membership: new subscription should create a draft invoice')
        self.assertEqual(
            invoice.invoice_line_ids[0].product_id, self.membership_1,
            'membership: new subscription should create a line with the membership as product')
        self.assertEqual(
            invoice.invoice_line_ids[0].price_unit, 75.0,
            'membership: new subscription should create a line with the given price instead of product price')

        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: old membership unpaid should be in non-member state')

        # the invoice is open -> customer goes to invoiced status
        invoice.action_post()

        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: after opening the invoice for old membership, it should remain in non paid status')

        # payment process
        payment = self.env['account.payment'].create({
            'destination_account_id': invoice.line_ids.account_id.filtered(lambda account: account.account_type == 'asset_receivable').id,
            'payment_method_line_id': self.inbound_payment_method_line.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'partner_id': invoice.partner_id.id,
            'amount': 500,
            'company_id': self.env.company.id,
            'currency_id': self.env.company.currency_id.id,
        })
        payment.action_post()
        inv1_receivable = invoice.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')
        pay_receivable = payment.move_id.line_ids.filtered(lambda l: l.account_id.account_type == 'asset_receivable')

        (inv1_receivable + pay_receivable).reconcile()

        # the invoice is paid -> customer goes to paid status
        self.assertEqual(
            self.partner_1.membership_state, 'old',
            'membership: after paying the invoice, customer should be in old status')

        # check second partner then associate them
        self.assertEqual(
            self.partner_2.membership_state, 'free',
            'membership: free member customer should be in free state')
        self.partner_2.write({'free_member': False, 'associate_member': self.partner_1.id})
        self.assertEqual(
            self.partner_2.membership_state, 'old',
            'membership: associated customer should be in old state')

    def test_paid_membership(self):
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: default membership status of partners should be None')

        # subscribes to a membership
        invoice = self.partner_1.create_membership_invoice(self.membership_1, 75.0)

        self.assertEqual(
            invoice.state, 'draft',
            'membership: new subscription should create a draft invoice')
        self.assertEqual(
            invoice.invoice_line_ids[0].product_id, self.membership_1,
            'membership: new subscription should create a line with the membership as product')
        self.assertEqual(
            invoice.invoice_line_ids[0].price_unit, 75.0,
            'membership: new subscription should create a line with the given price instead of product price')

        self.assertEqual(
            self.partner_1.membership_state, 'waiting',
            'membership: new membership should be in waiting state')

        # the invoice is open -> customer goes to invoiced status
        invoice.action_post()
        self.assertEqual(
            self.partner_1.membership_state, 'invoiced',
            'membership: after opening the invoice, customer should be in invoiced status')

        # the invoice is paid -> customer goes to paid status
        payment = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=invoice.ids)\
            .create({
                'amount': 86.25,
                'payment_method_line_id': self.inbound_payment_method_line.id,
            })\
            ._create_payments()

        self.assertEqual(
            self.partner_1.membership_state, 'paid',
            'membership: after paying the invoice, customer should be in paid status')

        # check second partner then associate them
        self.assertEqual(
            self.partner_2.membership_state, 'free',
            'membership: free member customer should be in free state')
        self.partner_2.write({'free_member': False, 'associate_member': self.partner_1.id})
        self.assertEqual(
            self.partner_2.membership_state, 'paid',
            'membership: associated customer should be in paid state')

    def test_cancel_membership(self):
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: default membership status of partners should be None')

        # subscribes to a membership
        invoice = self.partner_1.create_membership_invoice(self.membership_1, 75.0)

        def patched_today(*args, **kwargs):
            return fields.Date.to_date('2019-01-01')

        with patch.object(fields.Date, 'today', patched_today):
            invoice.button_cancel()

        self.partner_1._compute_membership_state()
        self.assertEqual(invoice.state, 'cancel')
        self.assertEqual(self.partner_1.membership_state, 'canceled')
