# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo import fields
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestAccountInvoiceRounding(AccountTestInvoicingCommon):
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
