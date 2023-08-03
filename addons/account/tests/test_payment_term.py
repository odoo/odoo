# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo import fields, Command
from odoo.tests.common import Form
from odoo.tools.safe_eval import datetime


@tagged('post_install', '-at_install')
class TestAccountPaymentTerms(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.pay_term_today = cls.env['account.payment.term'].create({
            'name': 'Today',
            'line_ids': [
                (0, 0, {
                    'value_amount': 100,
                    'value': 'percent',
                    'nb_days': 0,
                }),
            ],
        })

        cls.pay_term_net_30_days = cls.env['account.payment.term'].create({
            'name': 'Net 30 days',
            'line_ids': [
                (0, 0, {
                    'value_amount': 100,
                    'value': 'percent',
                    'nb_days': 30,
                }),
            ],
        })

        cls.pay_term_60_days = cls.env['account.payment.term'].create({
            'name': '60 days two lines',
            'line_ids': [
                (0, 0, {
                    'value_amount': 30,
                    'value': 'percent',
                    'nb_days': 15,
                }),
                (0, 0, {
                    'value_amount': 70,
                    'value': 'percent',
                    'nb_days': 45,
                }),
            ],
        })

        cls.pay_term_30_days = cls.env['account.payment.term'].create({
            'name': '60 days two lines',
            'line_ids': [
                (0, 0, {
                    'value_amount': 100,
                    'value': 'percent',
                    'nb_days': 15,
                }),
            ],
        })

        cls.invoice = cls.init_invoice('out_refund', products=cls.product_a+cls.product_b)

        cls.pay_term_a = cls.env['account.payment.term'].create({
            'name': "turlututu",
            'early_discount': True,
            'discount_percentage': 10,
            'discount_days': 1,
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 2,
                }),
            ],
        })

        cls.pay_term_b = cls.env['account.payment.term'].create({
            'name': "tralala",
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 50,
                    'nb_days': 2,
                }),
                Command.create({
                    'value': 'percent',
                    'value_amount': 50,
                    'nb_days': 4,
                }),
            ],
        })

    def assertPaymentTerm(self, pay_term, invoice_date, dates):
        with Form(self.invoice) as move_form:
            move_form.invoice_payment_term_id = pay_term
            move_form.invoice_date = invoice_date
        self.assertEqual(
            self.invoice.line_ids.filtered(
                lambda l: l.account_id == self.company_data['default_account_receivable']
            ).sorted(key=lambda r: r.date_maturity).mapped('date_maturity'),
            [fields.Date.from_string(date) for date in dates],
        )

    def test_payment_term(self):
        self.assertPaymentTerm(self.pay_term_today, '2019-01-01', ['2019-01-01'])
        self.assertPaymentTerm(self.pay_term_today, '2019-01-15', ['2019-01-15'])
        self.assertPaymentTerm(self.pay_term_today, '2019-01-31', ['2019-01-31'])

        self.assertPaymentTerm(self.pay_term_net_30_days, '2022-01-01', ['2022-01-31'])
        self.assertPaymentTerm(self.pay_term_net_30_days, '2022-01-15', ['2022-02-14'])
        self.assertPaymentTerm(self.pay_term_net_30_days, '2022-01-31', ['2022-03-02'])

        self.assertPaymentTerm(self.pay_term_60_days, '2022-01-01', ['2022-01-16', '2022-02-15'])
        self.assertPaymentTerm(self.pay_term_60_days, '2022-01-15', ['2022-01-30', '2022-03-01'])
        self.assertPaymentTerm(self.pay_term_60_days, '2022-01-31', ['2022-02-15', '2022-03-17'])

    def test_wrong_payment_term(self):
        with self.assertRaises(ValidationError):
            self.env['account.payment.term'].create({
                'name': 'Wrong Payment Term',
                'line_ids': [
                    (0, 0, {
                        'value': 'percent',
                        'value_amount': 50,
                    }),
                ],
            })

    def test_payment_term_compute_method_with_cash_discount(self):
        self.pay_term_a.early_pay_discount_computation = 'included'
        computed_term_a = self.pay_term_a._compute_terms(
                fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
                150.0, 150.0, 1000.0, 1000.0, 1.0,
            )
        self.assertDictEqual(
            {
                'total_amount': computed_term_a.get("total_amount"),
                'discount_balance': computed_term_a.get("discount_balance"),
                'line_ids': computed_term_a.get("line_ids"),
            },
            #What should be obtained
            {
                'total_amount': 1150.0,
                'discount_balance': 1035.0,
                'line_ids': [{
                    'date': datetime.date(2016, 1, 3),
                    'company_amount': 1150.0,
                    'foreign_amount': 151.0,
                }],
            },
        )

    def test_payment_term_compute_method_without_cash_discount(self):
        computed_term_b = self.pay_term_b._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            150.0, 150.0, 1000.0, 1000.0, 1.0,
        )
        self.assertDictEqual(
            {
                'total_amount': computed_term_b.get("total_amount"),
                'discount_balance': computed_term_b.get("discount_balance"),
                'line_ids': computed_term_b.get("line_ids"),
            },
            # What should be obtained
            {
                'total_amount': 1150.0,
                'discount_balance': 0,
                'line_ids': [{
                    'date': datetime.date(2016, 1, 3),
                    'company_amount': 575.0,
                    'foreign_amount': 75.5,
                }, {
                    'date': datetime.date(2016, 1, 5),
                    'company_amount': 575.0,
                    'foreign_amount': 75.5,
                }],
            },
        )

    def test_payment_term_compute_method_early_excluded(self):
        self.pay_term_a.early_pay_discount_computation = 'excluded'
        computed_term_a = self.pay_term_a._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            150.0, 150.0, 1000.0, 1000.0, 1.0,
        )

        self.assertDictEqual(
            {
                'total_amount': computed_term_a.get("total_amount"),
                'discount_balance': computed_term_a.get("discount_balance"),
                'line_ids': computed_term_a.get("line_ids"),
            },
            # What should be obtained
            {
                'total_amount': 1150.0,
                'discount_balance': 1050.0,
                'line_ids': [{
                    'date': datetime.date(2016, 1, 3),
                    'company_amount': 1150.0,
                    'foreign_amount': 151.0,
                }],
            },
        )

    def test_payment_term_residual_amount_on_last_line_with_fixed_amount_multi_currency(self):
        pay_term = self.env['account.payment.term'].create({
            'name': "test_payment_term_residual_amount_on_last_line",
            'line_ids': [
                Command.create({
                    'value_amount': 50,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 50,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 0.02,
                    'value': 'fixed',
                    'nb_days': 0,
                }),
            ],
        })

        computed_term = pay_term._compute_terms(
            fields.Date.from_string('2016-01-01'), self.currency_data['currency'], self.env.company,
            0.0, 0.0, 1.0, 0.04, 0.09,
        )
        self.assertEqual(
            [
                (
                    self.currency_data['currency'].round(l['foreign_amount']),
                    self.company_data['currency'].round(l['company_amount']),
                )
                for l in computed_term['line_ids']
            ],
            [(0.045, 0.02), (0.045, 0.02), (0.0, 0.0)],
        )

    def test_payment_term_residual_amount_on_last_line(self):
        pay_term = self.env['account.payment.term'].create({
            'name': "test_payment_term_residual_amount_on_last_line",
            'line_ids': [
                Command.create({
                    'value_amount': 50,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 50,
                    'value': 'percent',
                    'nb_days': 0,
                }),
            ],
        })

        computed_term = pay_term._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            0.0, 0.0, 1.0, 0.03, 0.03,
        )
        self.assertEqual(
            [self.env.company.currency_id.round(l['foreign_amount']) for l in computed_term['line_ids']],
            [0.02, 0.01],
        )

    def test_payment_term_last_balance_line_with_fixed(self):
        pay_term = self.env['account.payment.term'].create({
            'name': 'test_payment_term_last_balance_line_with_fixed',
            'line_ids': [
                Command.create({
                    'value_amount': 70,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 200,
                    'value': 'fixed',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 30,
                    'value': 'percent',
                    'nb_days': 0,
                }),
            ]
        })

        computed_term = pay_term._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            0.0, 0.0, 1.0, 1000.0, 1000.0,
        )

        self.assertEqual(
            [self.env.company.currency_id.round(l['foreign_amount']) for l in computed_term['line_ids']],
            [700.0, 200.0, 100.0],
        )

    def test_payment_term_last_balance_line_with_fixed_negative(self):
        pay_term = self.env['account.payment.term'].create({
            'name': 'test_payment_term_last_balance_line_with_fixed_negative',
            'line_ids': [
                Command.create({
                    'value_amount': 70,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 500,
                    'value': 'fixed',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 30,
                    'value': 'percent',
                    'nb_days': 0,
                }),
            ]
        })

        computed_term = pay_term._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            0.0, 0.0, 1.0, 1000.0, 1000.0,
        )

        self.assertEqual(
            [self.env.company.currency_id.round(l['foreign_amount']) for l in computed_term['line_ids']],
            [700.0, 500.0, -200.0],
        )

    def test_payment_term_last_balance_line_with_fixed_negative_fixed(self):
        pay_term = self.env['account.payment.term'].create({
            'name': 'test_payment_term_last_balance_line_with_fixed_negative_fixed',
            'line_ids': [
                Command.create({
                    'value_amount': 70,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 500,
                    'value': 'fixed',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 30,
                    'value': 'percent',
                    'nb_days': 0,
                }),
                Command.create({
                    'value_amount': 200,
                    'value': 'fixed',
                    'nb_days': 0,
                }),
            ]
        })

        computed_term = pay_term._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            0.0, 0.0, 1.0, 1000.0, 1000.0,
        )

        self.assertEqual(
            [self.env.company.currency_id.round(l['foreign_amount']) for l in computed_term['line_ids']],
            [700.0, 500.0, 300.0, -500.0],
        )

    def test_payment_term_percent_round_calculation(self):
        """
            the sum function might not sum the floating numbers properly
            if there are a lot of lines with floating numbers
            so this test verifies the round function changes
        """
        self.env['account.payment.term'].create({
            'name': "test_payment_term_percent_round_calculation",
            'line_ids': [
                Command.create({'value_amount': 50, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 1.66, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 16.8, 'value': 'percent', 'nb_days': 0, }),
            ],
        })
