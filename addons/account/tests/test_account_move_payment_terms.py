# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests.common import Form
from odoo.tests import tagged
from odoo import fields
from odoo.exceptions import UserError

from unittest.mock import patch


@tagged('post_install', '-at_install')
class TestAccountMovePaymentTerms(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.term_30_days = cls.env.ref('account.account_payment_term_30days')
        cls.term_30_in_advance = cls.env['account.payment.term'].create({
            'name': '30% Advance End of Following Month',
            'note': 'Payment terms: 30% Advance End of Following Month',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 30.0,
                    'sequence': 400,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
                (0, 0, {
                    'value': 'balance',
                    'value_amount': 0.0,
                    'sequence': 500,
                    'days': 31,
                    'option': 'day_following_month',
                }),
            ],
        })
        cls.zero_balance_payment_term = cls.env['account.payment.term'].create({
            'name': 'zero_balance_payment_term',
            'line_ids': [
                (0, 0, {
                    'value': 'percent',
                    'value_amount': 100.0,
                    'sequence': 10,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
                (0, 0, {
                    'value': 'balance',
                    'value_amount': 0.0,
                    'sequence': 20,
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
            ],
        })

        cls.zero_percent_tax = cls.env['account.tax'].create({
            'name': 'zero_percent_tax',
            'amount_type': 'percent',
            'amount': 0.0,
        })

        cls.custom_receivable_1 = cls.copy_account(cls.company_data['default_account_receivable'])
        cls.custom_receivable_2 = cls.copy_account(cls.company_data['default_account_receivable'])
        cls.custom_receivable_3 = cls.copy_account(cls.company_data['default_account_receivable'])

    def _test_payment_terms_30_days(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'price_unit': 2000.0,
                'price_subtotal': 2000.0,
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2000.0,
                'debit': 0.0,
                'credit': 1000.0,
                'date_maturity': False,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -300.0,
                'debit': 0.0,
                'credit': 150.0,
                'date_maturity': False,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 2300.0,
                'debit': 1150.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2019-01-31'),
            },
        ], {
            'invoice_payment_term_id': self.term_30_days.id,
            'invoice_date_due': fields.Date.from_string('2019-01-31'),
            'amount_untaxed': 2000.0,
            'amount_tax': 300.0,
            'amount_total': 2300.0,
        })

    def _test_payment_terms_30_in_advance(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'product_id': self.product_a.id,
                'price_unit': 2000.0,
                'price_subtotal': 2000.0,
                'tax_ids': self.product_a.taxes_id.ids,
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -2000.0,
                'debit': 0.0,
                'credit': 1000.0,
                'date_maturity': False,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': self.product_a.taxes_id.id,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': -300.0,
                'debit': 0.0,
                'credit': 150.0,
                'date_maturity': False,
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 690.0,
                'debit': 345.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2019-01-01'),
            },
            {
                'product_id': False,
                'price_unit': 0.0,
                'price_subtotal': 0.0,
                'tax_ids': [],
                'tax_line_id': False,
                'currency_id': self.currency_data['currency'].id,
                'amount_currency': 1610.0,
                'debit': 805.0,
                'credit': 0.0,
                'date_maturity': fields.Date.from_string('2019-02-28'),
            },
        ], {
            'invoice_payment_term_id': self.term_30_in_advance.id,
            'invoice_date_due': fields.Date.from_string('2019-02-28'),
            'amount_untaxed': 2000.0,
            'amount_tax': 300.0,
            'amount_total': 2300.0,
        })

    def _test_payment_terms_30_in_advance_new_invoice_date(self, invoice):
        self.assertRecordValues(invoice, [{
            'invoice_payment_term_id': self.term_30_in_advance.id,
            'invoice_date_due': fields.Date.from_string('2019-03-31'),
            'amount_untaxed': 2000.0,
            'amount_tax': 300.0,
            'amount_total': 2300.0,
        }])

    def test_create_payment_terms_flow(self):
        self.partner_a.property_payment_term_id = self.term_30_days

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'currency_id': self.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {
                'product_id': self.product_a.id,
                'tax_ids': [(6, 0, self.product_a.taxes_id.ids)],
            })],
        })

        self._test_payment_terms_30_days(invoice)

        invoice.invoice_payment_term_id = self.term_30_in_advance

        self._test_payment_terms_30_in_advance(invoice)

        invoice.invoice_date = '2019-02-01'

        self._test_payment_terms_30_in_advance_new_invoice_date(invoice)

    def test_onchange_payment_terms_flow(self):
        self.partner_a.property_payment_term_id = self.term_30_days

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.currency_id = self.currency_data['currency']
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
        invoice = move_form.save()

        self._test_payment_terms_30_days(invoice)

        with Form(invoice) as move_form:
            move_form.invoice_payment_term_id = self.term_30_in_advance

        self._test_payment_terms_30_in_advance(invoice)

        with Form(invoice) as move_form:
            move_form.invoice_date = '2019-02-01'

        self._test_payment_terms_30_in_advance_new_invoice_date(invoice)

    def _test_zero_balance_payment_term_zero_percent_tax(self, invoice):
        self.assertInvoiceValues(invoice, [
            {
                'tax_ids': self.zero_percent_tax.ids,
                'credit': 1000.0,
                'debit': 0.0,
            },
            {
                'tax_ids': [],
                'credit': 0.0,
                'debit': 1000.0,
            },
        ], {
            'amount_untaxed': 1000.0,
            'amount_tax': 0.0,
            'amount_total': 1000.0,
        })

    def test_create_zero_balance_payment_term_zero_percent_tax(self):
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_payment_term_id': self.zero_balance_payment_term.id,
            'invoice_line_ids': [(0, None, {
                'name': 'whatever',
                'quantity': 1.0,
                'price_unit': 1000.0,
                'tax_ids': [(6, 0, self.zero_percent_tax.ids)],
            })]
        })

        self._test_zero_balance_payment_term_zero_percent_tax(invoice)

    def test_onchange_zero_balance_payment_term_zero_percent_tax(self):
        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        move_form.invoice_payment_term_id = self.zero_balance_payment_term
        with move_form.invoice_line_ids.new() as line_form:
            line_form.name = 'whatever'
            line_form.price_unit = 1000.0
            line_form.tax_ids.clear()
            line_form.tax_ids.add(self.zero_percent_tax)
        invoice = move_form.save()

        self._test_zero_balance_payment_term_zero_percent_tax(invoice)

    def test_create_custom_receivable_account(self):
        ''' Ensure the user is free to edit the receivable/payable account. '''

        def assertReceivableAccount(invoice, accounts):
            payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type == 'receivable')
            self.assertRecordValues(payment_term_lines, [{'account_id': account.id} for account in accounts])

        self.partner_a.property_account_receivable_id = self.custom_receivable_1
        self.partner_b.property_account_receivable_id = self.custom_receivable_2

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'invoice_date': '2019-01-01',
            'invoice_line_ids': [(0, None, {'product_id': self.product_a.id})]
        })

        assertReceivableAccount(invoice, self.custom_receivable_1)

        payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type == 'receivable')
        invoice.write({'line_ids': [(1, payment_term_lines.id, {'account_id': self.custom_receivable_3.id})]})

        assertReceivableAccount(invoice, self.custom_receivable_3)

        invoice.partner_id = self.partner_b

        assertReceivableAccount(invoice, self.custom_receivable_2 + self.custom_receivable_2)

    def test_onchange_custom_receivable_account(self):
        ''' Ensure the user is free to edit the receivable/payable account. '''

        def assertReceivableAccount(invoice, accounts):
            payment_term_lines = invoice.line_ids.filtered(lambda line: line.account_internal_type == 'receivable')
            self.assertRecordValues(payment_term_lines, [{'account_id': account.id} for account in accounts])

        self.partner_a.property_account_receivable_id = self.custom_receivable_1
        self.partner_b.property_account_receivable_id = self.custom_receivable_2

        move_form = Form(self.env['account.move'].with_context(default_move_type='out_invoice'))
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string('2019-01-01')
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
        invoice = move_form.save()

        assertReceivableAccount(invoice, self.custom_receivable_1)

        pay_term_line_index = [line.account_internal_type for line in invoice.line_ids].index('receivable')
        with Form(invoice) as move_form:
            with move_form.line_ids.edit(pay_term_line_index) as line_form:
                line_form.account_id = self.custom_receivable_3
        assertReceivableAccount(invoice, self.custom_receivable_3)

        with Form(invoice) as move_form:
            move_form.partner_id = self.partner_b

        assertReceivableAccount(invoice, self.custom_receivable_2 + self.custom_receivable_2)
