# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo import fields, Command
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestAccountPaymentTerms(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.pay_term_today = cls.env['account.payment.term'].create({
            'name': 'Today',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                }),
            ],
        })

        cls.pay_term_next_month_on_the_15 = cls.env['account.payment.term'].create({
            'name': 'Next month on the 15th',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                    'end_month': True,
                    'days_after': 15,
                }),
            ],
        })

        cls.pay_term_last_day_of_month = cls.env['account.payment.term'].create({
            'name': 'Last Day of month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                    'end_month': True
                }),
            ],
        })

        cls.pay_term_first_day_next_month = cls.env['account.payment.term'].create({
            'name': 'First day next month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                    'end_month': True,
                    'days_after': 1,
                }),
            ],
        })

        cls.pay_term_net_30_days = cls.env['account.payment.term'].create({
            'name': 'Net 30 days',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 30,
                }),
            ],
        })

        cls.pay_term_30_days_end_of_month = cls.env['account.payment.term'].create({
            'name': '30 days end of month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 30,
                    'end_month': True
                }),
            ],
        })

        cls.pay_term_1_month_end_of_month = cls.env['account.payment.term'].create({
            'name': '1 month, end of month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'months': 1,
                    'days': 0,
                    'end_month': True
                }),
            ],
        })

        cls.pay_term_30_days_end_of_month_the_10 = cls.env['account.payment.term'].create({
            'name': '30 days end of month the 10th',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 30,
                    'end_month': True,
                    'days_after': 10,
                }),
            ],
        })

        cls.pay_term_90_days_end_of_month_the_10 = cls.env['account.payment.term'].create({
            'name': '90 days end of month the 10',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 90,
                    'end_month': True,
                    'days_after': 10,
                }),
            ],
        })

        cls.pay_term_3_months_end_of_month_the_10 = cls.env['account.payment.term'].create({
            'name': '3 months end of month the 10',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'months': 3,
                    'end_month': True,
                    'days_after': 10,
                }),
            ],
        })

        cls.pay_term_end_month_on_the_30th = cls.env['account.payment.term'].create({
            'name': 'End of month, the 30th',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'end_month': True,
                    'days_after': 30,
                }),
            ],
        })

        cls.pay_term_1_month_15_days_end_month_45_days = cls.env['account.payment.term'].create({
            'name': '1 month, 15 days, end month, 45 days',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'months': 1,
                    'days': 15,
                    'end_month': True,
                    'days_after': 45,
                }),
            ],
        })

        cls.pay_term_next_10_of_the_month = cls.env['account.payment.term'].create({
            'name': 'Next 10th of the month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'months': 0,
                    'days': -10,
                    'end_month': True,
                    'days_after': 10,
                }),
            ],
        })

        cls.invoice = cls.init_invoice('out_refund', products=cls.product_a+cls.product_b)

    def assertPaymentTerm(self, pay_term, invoice_date, dates):
        with Form(self.invoice) as move_form:
            move_form.invoice_payment_term_id = pay_term
            move_form.invoice_date = invoice_date
        self.assertEqual(
            self.invoice.line_ids.filtered(
                lambda l: l.account_id == self.company_data['default_account_receivable']
            ).mapped('date_maturity'),
            [fields.Date.from_string(date) for date in dates],
        )

    def test_payment_term(self):
        self.assertPaymentTerm(self.pay_term_today, '2019-01-01', ['2019-01-01'])
        self.assertPaymentTerm(self.pay_term_today, '2019-01-15', ['2019-01-15'])
        self.assertPaymentTerm(self.pay_term_today, '2019-01-31', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_next_month_on_the_15, '2019-01-01', ['2019-02-15'])
        self.assertPaymentTerm(self.pay_term_next_month_on_the_15, '2019-01-15', ['2019-02-15'])
        self.assertPaymentTerm(self.pay_term_next_month_on_the_15, '2019-01-31', ['2019-02-15'])
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-01', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-15', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-31', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-01', ['2019-02-01'])
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-15', ['2019-02-01'])
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-31', ['2019-02-01'])
        self.assertPaymentTerm(self.pay_term_net_30_days, '2022-01-01', ['2022-01-31'])
        self.assertPaymentTerm(self.pay_term_net_30_days, '2022-01-15', ['2022-02-14'])
        self.assertPaymentTerm(self.pay_term_net_30_days, '2022-01-31', ['2022-03-02'])
        self.assertPaymentTerm(self.pay_term_30_days_end_of_month, '2022-01-01', ['2022-01-31'])
        self.assertPaymentTerm(self.pay_term_30_days_end_of_month, '2022-01-15', ['2022-02-28'])
        self.assertPaymentTerm(self.pay_term_30_days_end_of_month, '2022-01-31', ['2022-03-31'])
        self.assertPaymentTerm(self.pay_term_1_month_end_of_month, '2022-01-01', ['2022-02-28'])
        self.assertPaymentTerm(self.pay_term_1_month_end_of_month, '2022-01-15', ['2022-02-28'])
        self.assertPaymentTerm(self.pay_term_1_month_end_of_month, '2022-01-31', ['2022-02-28'])
        self.assertPaymentTerm(self.pay_term_30_days_end_of_month_the_10, '2022-01-01', ['2022-02-10'])
        self.assertPaymentTerm(self.pay_term_30_days_end_of_month_the_10, '2022-01-15', ['2022-03-10'])
        self.assertPaymentTerm(self.pay_term_30_days_end_of_month_the_10, '2022-01-31', ['2022-04-10'])
        self.assertPaymentTerm(self.pay_term_90_days_end_of_month_the_10, '2022-01-01', ['2022-05-10'])
        self.assertPaymentTerm(self.pay_term_90_days_end_of_month_the_10, '2022-01-15', ['2022-05-10'])
        self.assertPaymentTerm(self.pay_term_90_days_end_of_month_the_10, '2022-01-31', ['2022-06-10'])
        self.assertPaymentTerm(self.pay_term_3_months_end_of_month_the_10, '2022-01-01', ['2022-05-10'])
        self.assertPaymentTerm(self.pay_term_3_months_end_of_month_the_10, '2022-01-15', ['2022-05-10'])
        self.assertPaymentTerm(self.pay_term_3_months_end_of_month_the_10, '2022-01-31', ['2022-05-10'])
        self.assertPaymentTerm(self.pay_term_1_month_15_days_end_month_45_days, '2022-01-01', ['2022-04-14'])
        self.assertPaymentTerm(self.pay_term_1_month_15_days_end_month_45_days, '2022-01-15', ['2022-05-15'])
        self.assertPaymentTerm(self.pay_term_1_month_15_days_end_month_45_days, '2022-01-31', ['2022-05-15'])
        self.assertPaymentTerm(self.pay_term_next_10_of_the_month, '2022-01-01', ['2022-01-10'])
        self.assertPaymentTerm(self.pay_term_next_10_of_the_month, '2022-01-09', ['2022-01-10'])
        self.assertPaymentTerm(self.pay_term_next_10_of_the_month, '2022-01-10', ['2022-01-10'])
        self.assertPaymentTerm(self.pay_term_next_10_of_the_month, '2022-01-15', ['2022-02-10'])
        self.assertPaymentTerm(self.pay_term_next_10_of_the_month, '2022-01-31', ['2022-02-10'])

    def test_payment_term_compute_method(self):
        def assert_payment_term_values(expected_values_list):
            res = pay_term._compute_terms(
                fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
                150, 150, 1000, 1000, 1,
            )
            self.assertEqual(len(res), len(expected_values_list))
            for values, (company_amount, discount_balance) in zip(res, expected_values_list):
                self.assertDictEqual(
                    {
                        'company_amount': values['company_amount'],
                        'discount_balance': values['discount_balance'],
                    },
                    {

                        'company_amount': company_amount,
                        'discount_balance': discount_balance,
                    },
                )

        pay_term = self.env['account.payment.term'].create({
            'name': "turlututu",
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 10,
                    'days': 2,
                    'discount_percentage': 10,
                    'discount_days': 1,
                }),
                Command.create({
                    'value': 'percent',
                    'value_amount': 20,
                    'days': 4,
                    'discount_percentage': 20,
                    'discount_days': 3,
                }),
                Command.create({
                    'value': 'percent',
                    'value_amount': 20,
                    'days': 6,
                }),
                Command.create({
                    'value': 'balance',
                    'days': 8,
                    'discount_percentage': 20,
                    'discount_days': 7,
                }),
            ],
        })

        self.env.company.early_pay_discount_computation = 'included'
        assert_payment_term_values([
            (115.0, 103.5),
            (230.0, 184.0),
            (230.0, 0.0),
            (575.0, 460.0),
        ])

        self.env.company.early_pay_discount_computation = 'excluded'
        assert_payment_term_values([
            (115.0, 105.0),
            (230.0, 190.0),
            (230.0, 0.0),
            (575.0, 475.0),
        ])
