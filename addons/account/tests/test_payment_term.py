# -*- coding: utf-8 -*-

from odoo.addons.account.tests.account_test_no_chart import TestAccountNoChartCommon
from odoo.tests import tagged
from odoo import fields


@tagged('post_install', '-at_install')
class TestAccountInvoiceRounding(TestAccountNoChartCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.setUpAdditionalAccounts()
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

        cls.invoice = cls.env['account.invoice'].create({
            'partner_id': cls.partner_customer_usd.id,
            'journal_id': cls.sale_journal0.id,
            'date_invoice': '2019-01-01',
            'invoice_line_ids': [(0, 0, {
                'name': 'name',
                'price_unit': 1,
                'account_id': cls.account_expense.id
            })]
        })

    def assertPaymentTerm(self, pay_term, date_invoice, dates):
        self.invoice.payment_term_id = pay_term
        self.invoice.date_invoice = date_invoice
        self.invoice.action_invoice_open()
        self.assertEqual(
            self.invoice.move_id.line_ids.filtered(lambda l: l.account_id == self.account_receivable).mapped('date_maturity'),
            [fields.Date.from_string(date) for date in dates],
        )

    def test_payment_term_01(self):
        self.assertPaymentTerm(self.pay_term_today, '2019-01-01', ['2019-01-01'])

    def test_payment_term_02(self):
        self.assertPaymentTerm(self.pay_term_today, '2019-01-15', ['2019-01-15'])

    def test_payment_term_03(self):
        self.assertPaymentTerm(self.pay_term_today, '2019-01-31', ['2019-01-31'])

    def test_payment_term_11(self):
        self.assertPaymentTerm(self.pay_term_45_end_month, '2019-01-01', ['2019-03-17'])

    def test_payment_term_12(self):
        self.assertPaymentTerm(self.pay_term_45_end_month, '2019-01-15', ['2019-03-17'])

    def test_payment_term_13(self):
        self.assertPaymentTerm(self.pay_term_45_end_month, '2019-01-31', ['2019-03-17'])

    def test_payment_term_21(self):
        self.assertPaymentTerm(self.pay_term_min_31days_15th, '2019-01-01', ['2019-02-15'])

    def test_payment_term_22(self):
        self.assertPaymentTerm(self.pay_term_min_31days_15th, '2019-01-15', ['2019-02-15'])

    def test_payment_term_23(self):
        self.assertPaymentTerm(self.pay_term_min_31days_15th, '2019-01-31', ['2019-03-15'])

    def test_payment_term_31(self):
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-01', ['2019-01-31'])

    def test_payment_term_32(self):
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-15', ['2019-01-31'])

    def test_payment_term_33(self):
        self.assertPaymentTerm(self.pay_term_last_day_of_month, '2019-01-31', ['2019-01-31'])

    def test_payment_term_41(self):
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-01', ['2019-02-01'])

    def test_payment_term_42(self):
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-15', ['2019-02-01'])

    def test_payment_term_43(self):
        self.assertPaymentTerm(self.pay_term_first_day_next_month, '2019-01-31', ['2019-02-01'])
