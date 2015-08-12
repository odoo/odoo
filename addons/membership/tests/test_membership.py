# -*- coding: utf-8 -*-

import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.membership.tests.common import TestMembershipCommon
from openerp.exceptions import AccessError, ValidationError, Warning
from openerp.tools import mute_logger


class TestMembership(TestMembershipCommon):

    def test_00_basic_membership(self):
        """ Basic membership flow """
        self.assertEqual(
            self.partner_1.membership_state, 'none',
            'membership: default membership status of partners should be None')

        # subscribes to a membership
        print '------------'
        self.partner_1.create_membership_invoice(product_id=self.membership_1.id, datas={'amount': 75.0})
        print '------------'

        # checks for invoices
        invoice = self.env['account.invoice'].search([('partner_id', '=', self.partner_1.id)], limit=1)[0]
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
        invoice.signal_workflow('invoice_open')
        self.assertEqual(
            self.partner_1.membership_state, 'invoiced',
            'membership: after opening the invoice, customer should be in invoiced status')

        # the invoice is paid -> customer goes to paid status
        bank_journals = self.env['account.journal'].search([('type', '=', 'bank')])
        invoice.pay_and_reconcile(bank_journals[0], invoice.amount_total)
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

        # refund invoice -> go into cancelled
        print invoice.payment_ids
        refund = self.env['account.invoice.refund'].with_context(active_id=invoice.id, active_ids=[invoice.id]).create({'description': 'Membership Refund', 'filter_refund': 'refund'})
        invoice.invalidate_cache()
        print refund
        refund.invoice_refund()
        print invoice, invoice.state
        print invoice.payment_ids

        refund_invoices = self.env['account.invoice'].search([('origin', '=', invoice.number)])
        print refund_invoices
        refund_invoices.signal_workflow('invoice_open')
        invoice.invalidate_cache()
        print invoice, invoice.state
        print invoice.payment_ids
