# -*- coding: utf-8 -*-

from odoo.addons.account.tests.common import AccountTestInvoicingCommon
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged
from odoo import fields, Command
from odoo.tools.safe_eval import datetime


@tagged('post_install', '-at_install')
class TestAccountPaymentTerms(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency('EUR', rounding=0.001)
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
                150.0, 150.0, 1.0, 1000.0, 1000.0,
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
                    'foreign_amount': 1150.0,
                }],
            },
        )

    def test_payment_term_compute_method_with_cash_discount_and_cash_rounding(self):
        foreign_currency = self.other_currency
        rate = self.env['res.currency']._get_conversion_rate(foreign_currency, self.env.company.currency_id, self.env.company, '2017-01-01')
        self.assertEqual(rate, 0.5)
        self.pay_term_a.early_pay_discount_computation = 'included'
        computed_term_a = self.pay_term_a._compute_terms(
            fields.Date.from_string('2016-01-01'), foreign_currency, self.env.company,
            75, 150, 1, 359.18, 718.35, cash_rounding=self.cash_rounding_a,
        )
        self.assertDictEqual(
            {
                'total_amount': computed_term_a.get("total_amount"),
                'discount_balance': computed_term_a.get("discount_balance"),
                'discount_amount_currency': computed_term_a.get("discount_amount_currency"),
                'line_ids': computed_term_a.get("line_ids"),
            },
            # What should be obtained
            {
                'total_amount': 434.18,
                'discount_balance': 390.78,
                'discount_amount_currency': 781.55,  # w/o cash rounding: 868.35 * 0.9 = 781.515
                'line_ids': [{
                    'date': datetime.date(2016, 1, 3),
                    'company_amount': 434.18,
                    'foreign_amount': 868.35,
                }],
            },
        )

    def test_payment_term_compute_method_without_cash_discount(self):
        computed_term_b = self.pay_term_b._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            150.0, 150.0, 1.0, 1000.0, 1000.0,
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
                    'foreign_amount': 575.0,
                }, {
                    'date': datetime.date(2016, 1, 5),
                    'company_amount': 575.0,
                    'foreign_amount': 575.0,
                }],
            },
        )

    def test_payment_term_compute_method_without_cash_discount_with_cash_rounding(self):
        foreign_currency = self.other_currency
        rate = self.env['res.currency']._get_conversion_rate(foreign_currency, self.env.company.currency_id, self.env.company, '2017-01-01')
        self.assertEqual(rate, 0.5)
        self.pay_term_a.early_pay_discount_computation = 'included'
        computed_term_b = self.pay_term_b._compute_terms(
            fields.Date.from_string('2016-01-01'), foreign_currency, self.env.company,
            75, 150, 1, 359.18, 718.35, cash_rounding=self.cash_rounding_a,
        )
        self.assertDictEqual(
            {
                'total_amount': computed_term_b.get("total_amount"),
                'discount_balance': computed_term_b.get("discount_balance"),
                'discount_amount_currency': computed_term_b.get("discount_amount_currency"),
                'line_ids': computed_term_b.get("line_ids"),
            },
            # What should be obtained
            {
                'total_amount': 434.18,
                'discount_balance': 0,
                'discount_amount_currency': None,
                'line_ids': [{
                    'date': datetime.date(2016, 1, 3),
                    'company_amount': 217.1,
                    'foreign_amount': 434.2,
                }, {
                    'date': datetime.date(2016, 1, 5),
                    'company_amount': 217.08,
                    'foreign_amount': 434.15000000000003,
                }],
            },
        )
        # Cash rounding should not affect the totals
        self.assertAlmostEqual(434.18, sum(line['company_amount'] for line in computed_term_b['line_ids']))
        self.assertAlmostEqual(868.35, sum(line['foreign_amount'] for line in computed_term_b['line_ids']))

    def test_payment_term_compute_method_early_excluded(self):
        self.pay_term_a.early_pay_discount_computation = 'excluded'
        computed_term_a = self.pay_term_a._compute_terms(
            fields.Date.from_string('2016-01-01'), self.env.company.currency_id, self.env.company,
            150.0, 150.0, 1.0, 1000.0, 1000.0,
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
                    'foreign_amount': 1150.0,
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
            fields.Date.from_string('2016-01-01'), self.other_currency, self.env.company,
            0.0, 0.0, 1.0, 0.04, 0.09,
        )
        self.assertEqual(
            [
                (
                    self.other_currency.round(l['foreign_amount']),
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

    def test_payment_term_labels(self):
        # create a payment term with 40% now, 30% in 30 days and 30% in 60 days
        multiple_installment_term = self.env['account.payment.term'].create({
            'name': "test_payment_term_labels",
            'line_ids': [
                Command.create({'value_amount': 40, 'value': 'percent', 'nb_days': 0, }),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 30, }),
                Command.create({'value_amount': 30, 'value': 'percent', 'nb_days': 60, }),
            ],
        })
        # create immediate payment term
        immediate_term = self.env['account.payment.term'].create({
            'name': 'Immediate',
            'line_ids': [
                Command.create({'value_amount': 100, 'value': 'percent', 'nb_days': 0, }),
            ],
        })
        # create an invoice with immediate payment term
        invoice = self.init_invoice('out_invoice', products=self.product_a)
        invoice.invoice_payment_term_id = immediate_term
        # check the payment term labels
        invoice_terms = invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term')
        self.assertEqual(invoice_terms[0].name, False)
        # change the payment term to the multiple installment term
        invoice.invoice_payment_term_id = multiple_installment_term
        invoice_terms = invoice.line_ids.filtered(lambda l: l.display_type == 'payment_term').sorted('date_maturity')
        self.assertEqual(invoice_terms[0].name, 'installment #1')
        self.assertEqual(invoice_terms[0].debit, invoice.amount_total * 0.4)
        self.assertEqual(invoice_terms[1].name, 'installment #2')
        self.assertEqual(invoice_terms[1].debit, invoice.amount_total * 0.3)
        self.assertEqual(invoice_terms[2].name, 'installment #3')
        self.assertEqual(invoice_terms[2].debit, invoice.amount_total * 0.3)

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

        expected_date_case_1 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_1, [fields.Date.from_string('2024-06-29')])

        with Form(self.invoice) as case_2:
            case_2.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            case_2.invoice_date = '2024-05-23'

        expected_date_case_2 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
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

        expected_date_case_1 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_1, [fields.Date.from_string('2024-07-30')])

        with Form(self.invoice) as case_2:
            case_2.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            case_2.invoice_date = '2024-05-23'

        expected_date_case_2 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_2, [fields.Date.from_string('2024-07-31')])

    def test_payment_term_days_end_of_month_days_next_month_0(self):
        with Form(self.invoice) as case_1:
            case_1.invoice_payment_term_id = self.pay_term_days_end_of_month_days_next_month_0
            case_1.invoice_date = '2024-04-22'

        expected_date_case_1 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data['default_account_receivable']).mapped('date_maturity')
        self.assertEqual(expected_date_case_1, [fields.Date.from_string('2024-05-31')])

    def test_payment_term_multi_company(self):
        """
        Ensure that the payment term is determined by `move.company_id` rather than `user.company_id`.
        OdooBot has `res.company(1)` set as the default company. The test checks that the payment term correctly reflects
        the company associated with the move, independent of the user's default company.
        """
        user_company = self.env['res.company'].create({'name': 'user_company'})
        other_company = self.company_data.get('company')
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
