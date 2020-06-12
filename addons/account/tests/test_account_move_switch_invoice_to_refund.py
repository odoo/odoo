# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo import fields
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountMoveSwitchInvoiceToRefund(AccountTestInvoicingCommon):

    def _test_switch_invoice_to_refund(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'tax_line_id': False,
                'tax_ids': self.tax_sale_a.ids,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2000.0,
                'credit': 0.0,
                'debit': 1000.0,
            },
            {
                'product_id': False,
                'tax_line_id': self.tax_sale_a.id,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 300.0,
                'credit': 0.0,
                'debit': 150.0,
            },
            {
                'product_id': False,
                'tax_line_id': False,
                'tax_ids': [],
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2300.0,
                'credit': 1150.0,
                'debit': 0.0,
            },
        ], {
            'move_type': 'out_refund',
            'currency_id': self.currency_data['currency'].id,
            'date': fields.Date.from_string('2017-01-01'),
            'invoice_date': fields.Date.from_string('2017-01-01'),
            'invoice_date_due': fields.Date.from_string('2017-01-01'),
            'amount_untaxed': 2000.0,
            'amount_tax': 300.0,
            'amount_total': 2300.0,
        })

    def test_switch_positive_invoice_to_refund(self):
        '''Test creating an account_move with an out_invoice_type and switch it in an out_refund.'''
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
            })],
        })
        invoice.action_switch_invoice_into_refund_credit_note()
        self._test_switch_invoice_to_refund(invoice)

    def test_switch_negative_invoice_to_refund(self):
        '''Test creating an account_move with an out_invoice_type and switch it in an out_refund and a negative
        quantity.
        '''
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2017-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'quantity': -1,
                'tax_ids': [(6, 0, self.tax_sale_a.ids)],
            })],
        })
        invoice.action_switch_invoice_into_refund_credit_note()
        self._test_switch_invoice_to_refund(invoice)
