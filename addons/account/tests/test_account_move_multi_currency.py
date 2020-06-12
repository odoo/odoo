# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMoveMultiCurrency(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.currency_data_2 = cls.setup_multi_currency_data(default_values={
            'name': 'Dark Chocolate Coin',
            'symbol': '🍫',
            'currency_unit_label': 'Dark Choco',
            'currency_subunit_label': 'Dark Cacao Powder',
        }, rate2016=6.0, rate2017=4.0)

        cls.currency_1 = cls.company_data['currency']
        cls.currency_2 = cls.currency_data['currency']
        cls.currency_3 = cls.currency_data_2['currency']

    def _test_no_currency(self, invoice):
        self.assertInvoiceValues(invoice, [
            {'debit': 0.0,      'credit': 2400.0,   'amount_currency': -2400.0,     'currency_id': self.currency_1.id},
            {'debit': 0.0,      'credit': 360.0,    'amount_currency': -360.0,      'currency_id': self.currency_1.id},
            {'debit': 2760.0,   'credit': 0.0,      'amount_currency': 2760.0,      'currency_id': self.currency_1.id},
        ], {
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
        })

    def _test_currency_2_2016(self, invoice):
        self.assertInvoiceValues(invoice, [
            {'debit': 0.0,      'credit': 800.0,    'amount_currency': -2400.0,    'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 120.0,    'amount_currency': -360.0,     'currency_id': self.currency_2.id},
            {'debit': 920.0,    'credit': 0.0,      'amount_currency': 2760.0,     'currency_id': self.currency_2.id},
        ], {
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
        })

    def _test_currency_2_2017(self, invoice):
        self.assertInvoiceValues(invoice, [
            {'debit': 0.0,      'credit': 1200.0,   'amount_currency': -2400.0,    'currency_id': self.currency_2.id},
            {'debit': 0.0,      'credit': 180.0,    'amount_currency': -360.0,     'currency_id': self.currency_2.id},
            {'debit': 1380.0,   'credit': 0.0,      'amount_currency': 2760.0,     'currency_id': self.currency_2.id},
        ], {
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
        })

    def _test_currency_3_2017(self, invoice):
        self.assertInvoiceValues(invoice, [
            {'debit': 0.0,      'credit': 600.0,    'amount_currency': -2400.0,    'currency_id': self.currency_3.id},
            {'debit': 0.0,      'credit': 90.0,     'amount_currency': -360.0,     'currency_id': self.currency_3.id},
            {'debit': 690.0,    'credit': 0.0,      'amount_currency': 2760.0,     'currency_id': self.currency_3.id},
        ], {
            'amount_untaxed': 2400.0,
            'amount_tax': 360.0,
            'amount_total': 2760.0,
        })

    def test_create_invoice_multi_currency_flow(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2016-01-01',
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'price_unit': 2400.0,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
            })],
        })
        self._test_no_currency(invoice)

        invoice.currency_id = self.currency_2
        self._test_currency_2_2016(invoice)

        invoice.invoice_date = '2017-01-01'
        self._test_currency_2_2017(invoice)

        invoice.currency_id = self.currency_3
        self._test_currency_3_2017(invoice)

        invoice.currency_id = self.currency_1
        self._test_no_currency(invoice)

    def test_onchange_invoice_multi_currency_flow(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2016-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.price_unit = 2400.0
        invoice = move_form.save()
        self._test_no_currency(invoice)

        with Form(invoice) as move_form:
            move_form.currency_id = self.currency_2
        self._test_currency_2_2016(invoice)

        with Form(invoice) as move_form:
            move_form.invoice_date = '2017-01-01'
        self._test_currency_2_2017(invoice)

        with Form(invoice) as move_form:
            move_form.currency_id = self.currency_3
        self._test_currency_3_2017(invoice)

        with Form(invoice) as move_form:
            move_form.currency_id = self.currency_1
        self._test_no_currency(invoice)
