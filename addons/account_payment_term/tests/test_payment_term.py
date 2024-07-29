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
            'name': "special case 31",
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
        cls.pay_term_days_end_of_month_30 = cls.env['account.payment.term'].create({
            'name': "special case 30",
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'delay_type': 'days_end_of_month_on_the',
                    'days_next_month': 30,
                    'nb_days': 0,
                }),
            ],
        })
        cls.pay_term_days_end_of_month_29 = cls.env['account.payment.term'].create({
            'name': "special case 29",
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'delay_type': 'days_end_of_month_on_the',
                    'days_next_month': 29,
                    'nb_days': 0,
                }),
            ],
        })
        cls.pay_term_days_end_of_month_days_next_month_0 = cls.env['account.payment.term'].create({
            'name': "special case days next month 0",
            'line_ids': [
                Command.create({
                    'value': 'percent',
                    'value_amount': 100,
                    'delay_type': 'days_end_of_month_on_the',
                    'days_next_month': 0,
                    'nb_days': 30,
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

    def test_payment_term_days_end_of_month_nb_days_0(self):
        """
        This test will check that payment terms with a delay_type 'days_end_of_month_on_the'
        in combination with nb_days works as expected

        Invoice date = 2024-05-23
        # case 1
        'nb_days' = 0
        `days_next_month` = 29
            -> 2024-05-23 + 0 days = 2024-05-23
            => `date_maturity` -> 2024-06-29
        # case 2
        'nb_days' = 0
        `days_next_month` = 31
            -> 2024-05-23 + 0 days = 2024-05-23
            => `date_maturity` -> 2024-06-30
        """
        self.pay_term_days_end_of_month_29.line_ids.nb_days = 0
        self.pay_term_days_end_of_month_31.line_ids.nb_days = 0
        with Form(self.invoice) as case_1:
            case_1.invoice_payment_term_id = self.pay_term_days_end_of_month_29
            case_1.invoice_date = '2024-05-23'

        expected_date_case_1 = self.invoice.line_ids.filtered(lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_1, [fields.Date.from_string('2024-06-29')])

        with Form(self.invoice) as case_2:
            case_2.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            case_2.invoice_date = '2024-05-23'

        expected_date_case_2 = self.invoice.line_ids.filtered(lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_2, [fields.Date.from_string('2024-06-30')])

    def test_payment_term_days_end_of_month_nb_days_15(self):
        """
        This test will check that payment terms with a delay_type 'days_end_of_month_on_the'
        in combination with nb_days works as expected

        Invoice date = 2024-05-23
        # case 1
        'nb_days' = 15
        `days_next_month` = 30
            -> 2024-05-23 + 15 days = 2024-06-07
            => `date_maturity` -> 2024-07-30
        # case 2
        'nb_days' = 15
        `days_next_month` = 31
            -> 2024-05-23 + 15 days = 2024-06-07
            => `date_maturity` -> 2024-07-31
        """
        self.pay_term_days_end_of_month_30.line_ids.nb_days = 15
        self.pay_term_days_end_of_month_31.line_ids.nb_days = 15

        with Form(self.invoice) as case_1:
            case_1.invoice_payment_term_id = self.pay_term_days_end_of_month_30
            case_1.invoice_date = '2024-05-24'

        expected_date_case_1 = self.invoice.line_ids.filtered(lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_1, [fields.Date.from_string('2024-07-30')])

        with Form(self.invoice) as case_2:
            case_2.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            case_2.invoice_date = '2024-05-23'

        expected_date_case_2 = self.invoice.line_ids.filtered(lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_2, [fields.Date.from_string('2024-07-31')])

    def test_payment_term_days_end_of_month_days_next_month_0(self):
        with Form(self.invoice) as case_1:
            case_1.invoice_payment_term_id = self.pay_term_days_end_of_month_days_next_month_0
            case_1.invoice_date = '2024-04-22'

        expected_date_case_1 = self.invoice.line_ids.filtered(lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_1, [fields.Date.from_string('2024-05-31')])
