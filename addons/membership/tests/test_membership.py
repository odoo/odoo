# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta
from unittest.mock import patch

from odoo.addons.membership.tests.common import TestMembershipCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestMembership(TestMembershipCommon):

    def test_old_membership(self):
        self.membership_1.write({
            'membership_date_from': datetime.date.today() + relativedelta(years=-2),
            'membership_date_to': datetime.date.today() + relativedelta(years=-1),
        })

        self.partner_1.create_membership_invoice(self.membership_1, 75.0)
        self.assertEqual(
            self.partner_1.membership_state, 'old',
            'membership: outdated subscription should put member in old state')

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
        invoice.post()
        self.assertEqual(
            self.partner_1.membership_state, 'invoiced',
            'membership: after opening the invoice, customer should be in invoiced status')

        # the invoice is paid -> customer goes to paid status
        bank_journal = self.env['account.journal'].create({'name': 'Bank', 'type': 'bank', 'code': 'BNK67'})
        self.env['account.payment'].create({
            'payment_method_id': self.env.ref("account.account_payment_method_manual_in").id,
            'payment_type': 'inbound',
            'invoice_ids': [(6, False, invoice.ids)],
            'amount': 86.25,
            'journal_id': bank_journal.id,
            'partner_type': 'customer',
        }).post()

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
