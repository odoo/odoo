# -*- coding: utf-8 -*-
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountPaymentTerm(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.pay_term_today = cls.env['account.payment.term'].create({
            'name': 'Today',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 0,
                    'option': 'day_after_invoice_date',
                }),
            ],
        })

        cls.pay_term_min_31days_15th = cls.env['account.payment.term'].create({
            'name': 'the 15th of the month, min 31 days from now',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 31,
                    'day_of_the_month': 15,
                    'option': 'day_after_invoice_date',
                }),
            ],
        })

        cls.pay_term_45_end_month = cls.env['account.payment.term'].create({
            'name': '45 Days from End of Month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 45,
                    'option': 'after_invoice_month',
                }),
            ],
        })

        cls.pay_term_last_day_of_month = cls.env['account.payment.term'].create({
            'name': 'Last Day of month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 31,
                    'option': 'day_current_month',
                }),
            ],
        })

        cls.pay_term_first_day_next_month = cls.env['account.payment.term'].create({
            'name': 'First day next month',
            'line_ids': [
                (0, 0, {
                    'value': 'balance',
                    'days': 1,
                    'option': 'day_following_month',
                }),
            ],
        })

    def assertPaymentTerm(self, payment_term, date, expected_dates):
        due_dates = [vals[0] for vals in payment_term.compute(1000.0, date_ref=date)]
        self.assertEqual(due_dates, expected_dates)

    def test_payment_term(self):
        self.assertPaymentTerm(self.pay_term_today, '2019-01-01', ['2019-01-01'])
        self.assertPaymentTerm(self.pay_term_today, '2019-01-15', ['2019-01-15'])
        self.assertPaymentTerm(self.pay_term_today, '2019-01-31', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_45_end_month, '2019-01-01', ['2019-03-17'])
        self.assertPaymentTerm(self.pay_term_45_end_month, '2019-01-15', ['2019-03-17'])
        self.assertPaymentTerm(self.pay_term_45_end_month, '2019-01-31', ['2019-03-17'])
        self.assertPaymentTerm(self.pay_term_min_31days_15th, '2019-01-01', ['2019-02-15'])
        self.assertPaymentTerm(self.pay_term_min_31days_15th, '2019-01-15', ['2019-02-15'])
        self.assertPaymentTerm(self.pay_term_min_31days_15th, '2019-01-31', ['2019-03-15'])
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-01', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-15', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-31', ['2019-01-31'])
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-01', ['2019-02-01'])
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-15', ['2019-02-01'])
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-31', ['2019-02-01'])
