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
                150, 150, 1, 1000, 1000,
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

    def test_payment_term_compute_method_cash_rounding(self):
        """Test that the payment terms are computed correctly in case we apply cash rounding.
        We check the amounts in document and company currency.
        We check that the cash rounding does not change the totals in document or company curreny.
        """
        def assert_payment_term_values(expected_values_list):
            foreign_currency = self.currency_data['currency']
            rate = self.env['res.currency']._get_conversion_rate(foreign_currency, self.env.company.currency_id, self.env.company, '2017-01-01')
            self.assertEqual(rate, 0.5)
            res = pay_term._compute_terms(
                fields.Date.from_string('2017-01-01'), foreign_currency, self.env.company,
                75, 150, 1, 359.18, 718.35, cash_rounding=self.cash_rounding_a
            )
            self.assertEqual(len(res), len(expected_values_list))

            keys = ['company_amount', 'discount_balance', 'foreign_amount', 'discount_amount_currency']
            for index, (values, expected_values) in enumerate(zip(res, expected_values_list)):
                for key in keys:
                    with self.subTest(index=index, key=key):
                        self.assertAlmostEqual(values[key], expected_values[key])

            total_company_amount = sum(value['company_amount'] for value in res)
            total_foreign_amount = sum(value['foreign_amount'] for value in res)
            self.assertAlmostEqual(total_company_amount, 434.18)
            self.assertAlmostEqual(total_foreign_amount, 868.35)

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

        with self.subTest(test='included'):
            self.env.company.early_pay_discount_computation = 'included'
            assert_payment_term_values([
                {
                    'company_amount': 43.43,
                    'discount_balance': 39.11,
                    'foreign_amount': 86.85,
                    'discount_amount_currency': 78.20,
                },
                {
                    'company_amount': 86.86,
                    'discount_balance': 69.51,
                    'foreign_amount': 173.70,
                    'discount_amount_currency': 139.00,
                },
                {
                    'company_amount': 86.86,
                    'discount_balance': 0,
                    'foreign_amount': 173.70,
                    'discount_amount_currency': 0.00,
                },
                {
                    'company_amount': 217.03,
                    'discount_balance': 173.63,
                    'foreign_amount': 434.10,
                    'discount_amount_currency': 347.30,
                },
               ])

        with self.subTest(test='excluded'):
            self.env.company.early_pay_discount_computation = 'excluded'
            assert_payment_term_values([
                {
                    'company_amount': 43.43,
                    'discount_balance': 39.86,
                    'foreign_amount': 86.85,
                    'discount_amount_currency': 79.70,
                },
                {
                    'company_amount': 86.86,
                    'discount_balance': 72.51,
                    'foreign_amount': 173.70,
                    'discount_amount_currency': 145.00,
                },
                {
                    'company_amount': 86.86,
                    'discount_balance': 0,
                    'foreign_amount': 173.70,
                    'discount_amount_currency': 0.00,
                },
                {
                    'company_amount': 217.03,
                    'discount_balance': 181.13,
                    'foreign_amount': 434.10,
                    'discount_amount_currency': 362.30,
                },
            ])

    def test_payment_term_multi_company(self):
        """
        Ensure that the payment term is determined by `move.company_id` rather than `user.company_id`.
        OdooBot has `res.company(1)` set as the default company. The test checks that the payment term correctly reflects
        the company associated with the move, independent of the user's default company.
        """
        user_company, other_company = self.company_data_2.get('company'), self.company_data.get('company')
        self.env.user.write({
            'company_ids': [user_company.id, other_company.id],
            'company_id': user_company.id,
        })
        self.pay_terms_a.company_id = user_company
        self.partner_a.with_company(user_company).property_payment_term_id = self.pay_terms_a
        self.partner_a.with_company(other_company).property_payment_term_id = False

        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self.partner_a.id,
            'company_id': other_company.id
        })
        self.assertFalse(invoice.invoice_payment_term_id)
