# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMoveCashRounding(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.cr_add_invoice_line = cls.env['account.cash.rounding'].create({
            'name': 'add_invoice_line',
            'rounding': 0.05,
            'strategy': 'add_invoice_line',
            'profit_account_id': cls.copy_account(cls.company_data['default_account_revenue']).id,
            'loss_account_id': cls.copy_account(cls.company_data['default_account_expense']).id,
            'rounding_method': 'UP',
        })

        cls.cr_biggest_tax = cls.env['account.cash.rounding'].create({
            'name': 'biggest_tax',
            'rounding': 0.05,
            'strategy': 'biggest_tax',
            'rounding_method': 'DOWN',
        })

    def _test_cash_rounding_add_invoice_line(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': False,
                'account_id': self.cr_add_invoice_line.profit_account_id.id,
                'tax_ids': [],
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 0.01,
            },
            {
                'product_id': self.product_a.id,
                'account_id': self.product_a.property_account_income_id.id,
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 999.99,
            },
            {
                'product_id': False,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'debit': 0.0,
                'credit': 150.0,
            },
            {
                'product_id': False,
                'account_id': self.partner_a.property_account_receivable_id.id,
                'tax_ids': [],
                'tax_line_id': False,
                'debit': 1150.0,
                'credit': 0.0,
            },
        ], {
            'invoice_cash_rounding_id': self.cr_add_invoice_line.id,
            'amount_untaxed': 1000.0,
            'amount_tax': 150.0,
            'amount_total': 1150.0,
        })

    def _test_cash_rounding_biggest_tax(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'account_id': self.product_a.property_account_income_id.id,
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'debit': 0.0,
                'credit': 999.99,
            },
            {
                'product_id': False,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'debit': 0.0,
                'credit': 150.0,
            },
            {
                'product_id': False,
                'account_id': self.company_data['default_account_tax_sale'].id,
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'debit': 0.04,
                'credit': 0.0,
            },
            {
                'product_id': False,
                'account_id': self.partner_a.property_account_receivable_id.id,
                'tax_ids': [],
                'tax_line_id': False,
                'debit': 1149.95,
                'credit': 0.0,
            },
        ], {
            'invoice_cash_rounding_id': self.cr_biggest_tax.id,
            'amount_untaxed': 999.99,
            'amount_tax': 149.96,
            'amount_total': 1149.95,
        })

    def test_create_cash_rounding_flow(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_cash_rounding_id': self.cr_add_invoice_line.id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 999.99,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
            })],
        })

        self._test_cash_rounding_add_invoice_line(invoice)

        invoice.invoice_cash_rounding_id = self.cr_biggest_tax

        self._test_cash_rounding_biggest_tax(invoice)

    def test_onchange_cash_rounding_flow(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.invoice_cash_rounding_id = self.cr_add_invoice_line
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.price_unit = 999.99
        invoice = move_form.save()

        self._test_cash_rounding_add_invoice_line(invoice)

        with Form(invoice) as move_form:
            move_form.invoice_cash_rounding_id = self.cr_biggest_tax

        self._test_cash_rounding_biggest_tax(invoice)
