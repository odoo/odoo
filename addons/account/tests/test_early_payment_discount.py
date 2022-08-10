# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields, Command


@tagged('post_install', '-at_install')
class TestAccountEarlyPaymentDiscount(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        # Payment Terms
        cls.default_pay_term_cash_discount = cls.env['account.payment.term'].create({
            'name': 'Default Early Payment Cash Discount Payment Term',
            'has_early_payment': True,
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
            ],
        })

        cls.pay_term_cash_discount_10_percent_10_days_tax_inc = cls.env['account.payment.term'].create({
            'name': '10% reduction if payment within 10 days, tax included',
            'has_early_payment': True,
            'discount_days': 10,
            'percentage_to_discount': 10,
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
            ],
        })
        cls.pay_term_cash_discount_10_percent_10_days_tax_excl = cls.env['account.payment.term'].create({
            'name': '10% reduction if payment within 10 days, tax excluded',
            'has_early_payment': True,
            'discount_days': 10,
            'percentage_to_discount': 10,
            'discount_computation': 'excluded',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
            ],
        })
        # Invoices (account move tests)
        cls.inv_1200_10_percents_discount_no_tax = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'line',
                'price_unit': 1200.0,
                'tax_ids': []
            })],
            'invoice_payment_term_id': cls.pay_term_cash_discount_10_percent_10_days_tax_inc.id,
        })
        cls.inv_1500_10_percents_discount_tax_incl_15_percents_tax = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'line',
                'price_unit': 1500.0,
                'tax_ids': [Command.set(cls.product_a.taxes_id.ids)],# 15%
            })],
            'invoice_payment_term_id': cls.pay_term_cash_discount_10_percent_10_days_tax_inc.id,
        })
        cls.inv_1500_10_percents_discount_tax_excl_15_percents_tax = cls.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_date': '2019-01-01',
            'date': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'line',
                'price_unit': 1500.0,
                'tax_ids': [Command.set(cls.product_a.taxes_id.ids)],# 15%
            })],
            'invoice_payment_term_id': cls.pay_term_cash_discount_10_percent_10_days_tax_excl.id,
        })
        # Invoices (Payment Register & reconciliation tests)
        # -- Customer invoices sharing the same batch
        cls.out_invoice_1 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 1000.0, 'tax_ids': []})],
            'invoice_payment_term_id': cls.default_pay_term_cash_discount.id,
        })
        cls.out_invoice_2 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_a.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 2000.0, 'tax_ids': []})],
            'invoice_payment_term_id': cls.default_pay_term_cash_discount.id,
        })
        #--Customer invoices from a different batch
        cls.out_invoice_3 = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_b.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 3000.0, 'tax_ids': []})],
            'invoice_payment_term_id': cls.default_pay_term_cash_discount.id,
        })
        cls.out_invoice_4_no_discount = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'date': '2017-01-01',
            'invoice_date': '2017-01-01',
            'partner_id': cls.partner_b.id,
            'currency_id': cls.currency_data['currency'].id,
            'invoice_line_ids': [(0, 0, {'product_id': cls.product_a.id, 'price_unit': 5000.0, 'tax_ids': []})],
            'invoice_payment_term_id': None,
        })

        (cls.out_invoice_1 + cls.out_invoice_2 + cls.out_invoice_3 + cls.out_invoice_4_no_discount).action_post()

        # Taxes
        cls.tax_10 = cls.env['account.tax'].create({
            'name': "tax_10",
            'amount_type': 'percent',
            'amount': 10.0,
        })

        cls.tax_20 = cls.env['account.tax'].create({
            'name': "tax_20",
            'amount_type': 'percent',
            'amount': 20.0,
        })
        lines_data = [
            (1100, cls.tax_10 + cls.tax_20),
            (1100, cls.tax_10),
            (1000, cls.tax_20),
        ]
        invoice_lines_vals = [
            (0, 0, {
                'name': 'line',
                'account_id': cls.company_data['default_account_revenue'].id,
                'price_unit': amount,
                'tax_ids': [(6, 0, taxes.ids)],
            })
        for amount, taxes in lines_data]
        cls.taxed_invoice = cls.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': cls.partner_a.id,
            'invoice_line_ids': invoice_lines_vals,
            'invoice_payment_term_id': cls.pay_term_cash_discount_10_percent_10_days_tax_inc.id,
        })

    # ========================== Tests Payment Terms ==========================
    def test_early_payment_assert_default_values(self):
        # Check that the early discount payment term is correctly set by default
        self.assertRecordValues(self.default_pay_term_cash_discount, [{
            'discount_computation': 'included',
            'discount_days': 7,
            'percentage_to_discount': 2.0
        }])

    def test_early_payment_end_date(self):
        # Check that the last date of the cash discount availability is correctly computed.
        # The default time delay is 7 days after the invoice.
        def assertEarlyDiscountPaymentTermDate(pay_term, move_date, expected_date):
            self.assertEqual(
                pay_term._get_last_date_for_discount(fields.Date.from_string(move_date)),
                fields.Date.from_string(expected_date)
            )
        assertEarlyDiscountPaymentTermDate(self.default_pay_term_cash_discount, '2022-01-01', '2022-01-08')
        assertEarlyDiscountPaymentTermDate(self.default_pay_term_cash_discount, '2022-01-31', '2022-02-07')
        assertEarlyDiscountPaymentTermDate(self.default_pay_term_cash_discount, '2022-02-25', '2022-03-04')

    # ========================== Tests Account Move ==========================
    def test_early_pay_reduced_amounts(self):
        # Check that the monetary amounts after the discount are correct.
        # 1200 invoice, no tax, 10% discount
        self.assertRecordValues(self.inv_1200_10_percents_discount_no_tax, [{
            'invoice_early_pay_amount_after_discount': 1080.00,
        }])
        # 1500 invoice, 15% tax, 10% discount including taxes
        self.assertRecordValues(self.inv_1500_10_percents_discount_tax_incl_15_percents_tax, [{
            'invoice_early_pay_amount_after_discount': 1552.50,
        }])
        # 1500 invoice, 15% tax, 10% discount excluding taxes
        self.assertRecordValues(self.inv_1500_10_percents_discount_tax_excl_15_percents_tax, [{
            'invoice_early_pay_amount_after_discount': 1575.0,
        }])

    # ========================== Tests Payment Register ==========================
    def test_register_discounted_payment_on_single_invoice(self):
        active_ids = self.out_invoice_1.ids
        payments = self.env['account.payment.register'].with_context(active_model='account.move', active_ids=active_ids).create({
            'payment_date': '2017-01-01',
            'early_pay_discount_toggle_button': True,
        })._create_payments()

        self.assertTrue(payments.is_reconciled)
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -1000.0},
            {
                'account_id': self.env.company['account_journal_cash_discount_expense_id'].id,
                'amount_currency': 20.0,
            },
            {'amount_currency': 980.0},
        ])

    def test_register_discounted_payment_on_batched_invoice(self):
        active_ids = (self.out_invoice_1 + self.out_invoice_2).ids
        payment_register = self.env['account.payment.register']\
            .with_context(active_model='account.move', active_ids=active_ids)\
            .create({
                'payment_date': '2017-01-01',
                'early_pay_discount_toggle_button': True,
            })
        payments = payment_register._create_payments()
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -2000.0},
            {'amount_currency': -1000.0},
            {
                'account_id': self.env.company['account_journal_cash_discount_expense_id'].id,
                'amount_currency': 20.0,
            },
            {
                'account_id': self.env.company['account_journal_cash_discount_expense_id'].id,
                'amount_currency': 40.0,
            },
            {'amount_currency': 980.0},
            {'amount_currency': 1960.0},
        ])

        self.assertTrue(all(p.is_reconciled for p in payments))

    def test_register_discounted_payment_on_non_batched_invoice(self):
        active_ids = (self.out_invoice_1 + self.out_invoice_2 + self.out_invoice_3).ids
        payment_register = self.env['account.payment.register'] \
            .with_context(active_model='account.move', active_ids=active_ids) \
            .create({
            'payment_date': '2017-01-01',
            'early_pay_discount_toggle_button': True,
        })
        payments = payment_register._create_payments()
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -3000.0},
            {'amount_currency': -2000.0},
            {'amount_currency': -1000.0},
            {
                'account_id': self.env.company['account_journal_cash_discount_expense_id'].id,
                'amount_currency': 20.0,
            },
            {
                'account_id': self.env.company['account_journal_cash_discount_expense_id'].id,
                'amount_currency': 40.0,
            },
            {
                'account_id': self.env.company['account_journal_cash_discount_expense_id'].id,
                'amount_currency': 60.0,
            },
            {'amount_currency': 980.0},
            {'amount_currency': 1960.0},
            {'amount_currency': 2940.0},
        ])
        self.assertTrue(all(p.is_reconciled for p in payments))

    def test_register_discounted_payment_on_non_batched_invoice_one_no_discount(self):
        active_ids = (self.out_invoice_3 + self.out_invoice_4_no_discount).ids
        payment_register = self.env['account.payment.register'] \
            .with_context(active_model='account.move', active_ids=active_ids) \
            .create({
                'payment_date': '2017-01-01',
                'early_pay_discount_toggle_button': True,
            })
        payments = payment_register._create_payments()
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -5000.0},
            {'amount_currency': -3000.0},
            {
                'account_id': self.env.company['account_journal_cash_discount_expense_id'].id,
                'amount_currency': 60.0,
            },
            {'amount_currency': 2940.0},
            {'amount_currency': 5000.0},
        ])
        self.assertTrue(all(p.is_reconciled for p in payments))

    def test_register_payment_deactivate_discount(self):
        active_ids = self.out_invoice_3.ids
        payment_register = self.env['account.payment.register'] \
            .with_context(active_model='account.move', active_ids=active_ids) \
            .create({
            'payment_date': '2017-01-01',
            'early_pay_discount_toggle_button': False,
        })
        payments = payment_register._create_payments()
        self.assertRecordValues(payments.line_ids.sorted('balance'), [
            {'amount_currency': -3000.0},
            {'amount_currency': 3000.0},
        ])
        self.assertTrue(payments.is_reconciled)

    def test_early_payment_taxes_computation(self):
        result = self.taxed_invoice._get_report_early_payment_totals_values()
        self.assertEqual(result['amount_total'], 3456)
        self.assertEqual(result['amount_untaxed'], 2880)
        self.assertEqual(result['groups_by_subtotal']['Untaxed Amount'][0]['tax_group_amount'], 576)
