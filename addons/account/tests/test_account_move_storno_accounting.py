# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountMoveStornoAccounting(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.company_data['company'].use_storno_accounting = True

    def _test_storno_generated_refund(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2000.0,
                'debit': 0.0,
                'credit': -1000.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 300.0,
                'debit': 0.0,
                'credit': -150.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2300.0,
                'debit': -1150.0,
                'credit': 0.0,
            },
        ], {
            'amount_untaxed': 2000.0,
            'amount_tax': 300.0,
            'amount_total': 2300.0,
        })

    def test_storno_create_generated_refund(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
            })],
        })

        self._test_storno_generated_refund(invoice)

    def test_storno_onchange_generated_refund(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_refund'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        invoice = move_form.save()

        self._test_storno_generated_refund(invoice)

    def test_storno_reversed_bill(self):
        invoice = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
            })],
        })
        invoice.action_post()

        move_reversal = self.env['account.move.reversal']\
            .with_context(active_model="account.move", active_ids=invoice.ids)\
            .create({
                'date': '2017-01-01',
                'reason': 'no reason',
                'refund_method': 'cancel',
            })
        reversal = move_reversal.reverse_moves()
        refund = self.env['account.move'].browse(reversal['res_id'])

        self.assertInvoiceValues(refund, [
            {
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2400.0,
                'debit': -1200.0,
                'credit': 0.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -360.0,
                'debit': -180.0,
                'credit': 0.0,
            },
            {
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2760.0,
                'debit': 0.0,
                'credit': -1380.0,
            },
        ], {
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
            'amount_residual': 0.0,
        })

    def test_storno_cash_basis_taxes(self):
        cash_basis_tax = self.env['account.tax'].create({
            'name': 'cash_basis_tax',
            'amount': 15.0,
            'company_id': self.company_data['company'].id,
            'tax_exigibility': 'on_payment',
        })

        refund = self.env['account.move'].create({
            'move_type': 'out_refund',
            'partner_id': self.partner_a.id,
            'invoice_date': '2016-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, cash_basis_tax.ids)],
            })],
        })
        refund.action_post()

        self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=refund.ids)\
            .create({})\
            ._create_payments()

        # Refund should be paid.
        self.assertRecordValues(refund, [{'amount_residual': 0.0}])

        cash_basis_move = self.env['account.move'].search([('tax_cash_basis_move_id', '=', refund.id)])

        self.assertTrue(cash_basis_move)
        self.assertRecordValues(cash_basis_move, [{
            'use_storno_accounting': True,
        }])
        self.assertRecordValues(cash_basis_move.line_ids, [
            {'debit': -1500.0,  'credit': 0.0,          'amount_currency': -3000.0},
            {'debit': 0.0,      'credit': -1500.0,      'amount_currency': 3000.0},
            {'debit': -225.0,   'credit': 0.0,          'amount_currency': -450.0},
            {'debit': 0.0,      'credit': -225.0,       'amount_currency': 450.0},
        ])
