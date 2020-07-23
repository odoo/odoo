# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta

from odoo.addons.membership.tests.common import TestMembershipCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestMembership(TestMembershipCommon):

    def test_none_membership(self):
        self.membership_1.write({
            'membership_date_from': datetime.date.today() + relativedelta(years=-2),
            'membership_date_to': datetime.date.today() + relativedelta(years=-1),
        })

        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: outdated non paid subscription should keep in non-member state')

    def test_old_membership(self):
        self.membership_1.write({
            'membership_date_from': datetime.date.today() + relativedelta(years=-2),
            'membership_date_to': datetime.date.today() + relativedelta(years=-1),
        })

        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: outdated non paid subscription should keep in non-member state')

        # subscribes to a membership
        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})

        # checks for invoices
        invoice = self.env['account.invoice'].search([('partner_id', '=', self.partner_1.id)], limit=1)
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
        invoice.action_invoice_open()
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: after opening the invoice for old membership, it should remain in non paid status')

        # the invoice is paid -> customer goes to paid status
        bank_journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        invoice.pay_and_reconcile(bank_journal, invoice.amount_total)
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
        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})

        # checks for invoices
        invoice = self.env['account.invoice'].search([('partner_id', '=', self.partner_1.id)], limit=1)
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
        invoice.action_invoice_open()
        self.assertEqual(
            self.partner_1.membership_state, 'invoiced',
            'membership: after opening the invoice, customer should be in invoiced status')

        # the invoice is paid -> customer goes to paid status
        bank_journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        invoice.pay_and_reconcile(bank_journal, invoice.amount_total)
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
        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})

        # checks for invoices
        invoice = self.env['account.invoice'].search([('partner_id', '=', self.partner_1.id)], limit=1)

        # the invoice is canceled -> membership state of the customer goes to canceled
        invoice.action_invoice_cancel()
        self.assertEqual(invoice.state, 'cancel')
        self.assertEqual(self.partner_1.membership_state, 'canceled')
