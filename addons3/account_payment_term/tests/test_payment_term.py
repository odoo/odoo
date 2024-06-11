from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.tests import tagged
from odoo.tests.common import Form


@tagged('post_install', '-at_install')
class TestAccountPaymentTerms(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)

        cls.invoice = cls.init_invoice('out_refund', products=cls.product_a + cls.product_b)

        cls.pay_term_days_end_of_month_10 = cls.env['account.payment.term'].create({
            'name': "basic case",
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 30,
                    'delay_type': 'days_end_of_month_on_the',
                    'days_next_month': 10,
                }),
            ],
        })
        cls.pay_term_days_end_of_month_31 = cls.env['account.payment.term'].create({
            'name': "special case",
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'nb_days': 30,
                    'delay_type': 'days_end_of_month_on_the',
                    'days_next_month': 31,
                }),
            ],
        })

    def test_payment_term_days_end_of_month_on_the(self):
        """
            This test will check that payment terms with a delay_type 'days_end_of_month_on_the' works as expected.
            It will check if the date of the date maturity is correctly calculated depending on the invoice date and payment
            term selected.
        """
        with Form(self.invoice) as basic_case:
            basic_case.invoice_payment_term_id = self.pay_term_days_end_of_month_10
            basic_case.invoice_date = '2023-12-12'

        expected_date_basic_case = self.invoice.line_ids.filtered(lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity'),
        self.assertEqual(expected_date_basic_case[0], [fields.Date.from_string('2024-02-10')])

        with Form(self.invoice) as special_case:
            special_case.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            special_case.invoice_date = '2023-12-12'

        expected_date_special_case = self.invoice.line_ids.filtered(lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity'),
        self.assertEqual(expected_date_special_case[0], [fields.Date.from_string('2024-02-29')])
