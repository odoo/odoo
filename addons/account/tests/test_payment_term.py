from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import Form, tagged
from odoo.tools import format_date, formatLang
from odoo.tools.safe_eval import datetime

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountPaymentTerms(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_currency = cls.setup_other_currency("EUR", rounding=0.001)
        cls.pay_term_today = cls.env["account.payment.term"].create(
            {
                "name": "Today",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value_amount": 100,
                            "value": "percent",
                            "nb_days": 0,
                        },
                    ),
                ],
            }
        )

        cls.pay_term_net_30_days = cls.env["account.payment.term"].create(
            {
                "name": "Net 30 days",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value_amount": 100,
                            "value": "percent",
                            "nb_days": 30,
                        },
                    ),
                ],
            }
        )

        cls.pay_term_60_days = cls.env["account.payment.term"].create(
            {
                "name": "60 days two lines",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value_amount": 30,
                            "value": "percent",
                            "nb_days": 15,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "value_amount": 70,
                            "value": "percent",
                            "nb_days": 45,
                        },
                    ),
                ],
            }
        )

        cls.pay_term_30_days = cls.env["account.payment.term"].create(
            {
                "name": "60 days two lines",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "value_amount": 100,
                            "value": "percent",
                            "nb_days": 15,
                        },
                    ),
                ],
            }
        )

        cls.invoice = cls.init_invoice(
            "out_refund", products=cls.product_a + cls.product_b
        )

        cls.pay_term_a = cls.env["account.payment.term"].create(
            {
                "name": "turlututu",
                "early_discount": True,
                "discount_percentage": 10,
                "discount_days": 1,
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "nb_days": 2,
                        }
                    ),
                ],
            }
        )

        cls.pay_term_b = cls.env["account.payment.term"].create(
            {
                "name": "tralala",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 50,
                            "nb_days": 2,
                        }
                    ),
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 50,
                            "nb_days": 4,
                        }
                    ),
                ],
            }
        )

        cls.pay_term_days_end_of_month_10 = cls.env["account.payment.term"].create(
            {
                "name": "basic case",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "nb_days": 30,
                            "delay_type": "days_end_of_month_on_the",
                            "days_next_month": 10,
                        }
                    ),
                ],
            }
        )
        cls.pay_term_days_end_of_month_31 = cls.env["account.payment.term"].create(
            {
                "name": "special case 31",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "nb_days": 30,
                            "delay_type": "days_end_of_month_on_the",
                            "days_next_month": 31,
                        }
                    ),
                ],
            }
        )
        cls.pay_term_days_end_of_month_30 = cls.env["account.payment.term"].create(
            {
                "name": "special case 30",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "delay_type": "days_end_of_month_on_the",
                            "days_next_month": 30,
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )
        cls.pay_term_days_end_of_month_29 = cls.env["account.payment.term"].create(
            {
                "name": "special case 29",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "delay_type": "days_end_of_month_on_the",
                            "days_next_month": 29,
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )
        cls.pay_term_days_end_of_month_days_next_month_0 = cls.env[
            "account.payment.term"
        ].create(
            {
                "name": "special case days next month 0",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 100,
                            "delay_type": "days_end_of_month_on_the",
                            "days_next_month": 0,
                            "nb_days": 30,
                        }
                    ),
                ],
            }
        )

    def assertPaymentTerm(self, pay_term, invoice_date, dates):
        with Form(self.invoice) as move_form:
            move_form.invoice_payment_term_id = pay_term
            move_form.invoice_date = invoice_date
        self.assertEqual(
            self.invoice.line_ids.filtered(
                lambda l: (
                    l.account_id == self.company_data["default_account_receivable"]
                )
            )
            .sorted(key=lambda r: r.date_maturity)
            .mapped("date_maturity"),
            [fields.Date.from_string(date) for date in dates],
        )

    def test_payment_term(self):
        self.assertPaymentTerm(self.pay_term_today, "2019-01-01", ["2019-01-01"])
        self.assertPaymentTerm(self.pay_term_today, "2019-01-15", ["2019-01-15"])
        self.assertPaymentTerm(self.pay_term_today, "2019-01-31", ["2019-01-31"])

        self.assertPaymentTerm(self.pay_term_net_30_days, "2022-01-01", ["2022-01-31"])
        self.assertPaymentTerm(self.pay_term_net_30_days, "2022-01-15", ["2022-02-14"])
        self.assertPaymentTerm(self.pay_term_net_30_days, "2022-01-31", ["2022-03-02"])

        self.assertPaymentTerm(
            self.pay_term_60_days, "2022-01-01", ["2022-01-16", "2022-02-15"]
        )
        self.assertPaymentTerm(
            self.pay_term_60_days, "2022-01-15", ["2022-01-30", "2022-03-01"]
        )
        self.assertPaymentTerm(
            self.pay_term_60_days, "2022-01-31", ["2022-02-15", "2022-03-17"]
        )

    def test_wrong_payment_term(self):
        with self.assertRaises(ValidationError):
            self.env["account.payment.term"].create(
                {
                    "name": "Wrong Payment Term",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "value": "percent",
                                "value_amount": 50,
                            },
                        ),
                    ],
                }
            )

    def test_payment_term_compute_method_with_cash_discount(self):
        self.pay_term_a.early_pay_discount_computation = "included"
        computed_term_a = self.pay_term_a._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.env.company.currency_id,
            company=self.env.company,
            tax_amount=150.0,
            tax_amount_currency=150.0,
            sign=1.0,
            untaxed_amount=1000.0,
            untaxed_amount_currency=1000.0,
        )
        self.assertDictEqual(
            {
                "total_amount": computed_term_a.get("total_amount"),
                "discount_balance": computed_term_a.get("discount_balance"),
                "line_ids": computed_term_a.get("line_ids"),
            },
            {
                "total_amount": 1150.0,
                "discount_balance": 1035.0,
                "line_ids": [
                    {
                        "date": datetime.date(2016, 1, 3),
                        "company_amount": 1150.0,
                        "foreign_amount": 1150.0,
                    }
                ],
            },
        )

    def test_payment_term_compute_method_with_cash_discount_and_cash_rounding(self):
        foreign_currency = self.other_currency
        rate = self.env["res.currency"]._get_conversion_rate(
            foreign_currency,
            self.env.company.currency_id,
            self.env.company,
            "2017-01-01",
        )
        self.assertEqual(rate, 0.5)
        self.pay_term_a.early_pay_discount_computation = "included"
        computed_term_a = self.pay_term_a._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=foreign_currency,
            company=self.env.company,
            tax_amount=75,
            tax_amount_currency=150,
            sign=1,
            untaxed_amount=359.18,
            untaxed_amount_currency=718.35,
            cash_rounding=self.cash_rounding_a,
        )
        self.assertDictEqual(
            {
                "total_amount": computed_term_a.get("total_amount"),
                "discount_balance": computed_term_a.get("discount_balance"),
                "discount_amount_currency": computed_term_a.get(
                    "discount_amount_currency"
                ),
                "line_ids": computed_term_a.get("line_ids"),
            },
            {
                "total_amount": 434.18,
                "discount_balance": 390.78,
                "discount_amount_currency": 781.55,
                "line_ids": [
                    {
                        "date": datetime.date(2016, 1, 3),
                        "company_amount": 434.18,
                        "foreign_amount": 868.35,
                    }
                ],
            },
        )

    def test_payment_term_compute_method_without_cash_discount(self):
        computed_term_b = self.pay_term_b._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.env.company.currency_id,
            company=self.env.company,
            tax_amount=150.0,
            tax_amount_currency=150.0,
            sign=1.0,
            untaxed_amount=1000.0,
            untaxed_amount_currency=1000.0,
        )
        self.assertDictEqual(
            {
                "total_amount": computed_term_b.get("total_amount"),
                "discount_balance": computed_term_b.get("discount_balance"),
                "line_ids": computed_term_b.get("line_ids"),
            },
            {
                "total_amount": 1150.0,
                "discount_balance": 0,
                "line_ids": [
                    {
                        "date": datetime.date(2016, 1, 3),
                        "company_amount": 575.0,
                        "foreign_amount": 575.0,
                    },
                    {
                        "date": datetime.date(2016, 1, 5),
                        "company_amount": 575.0,
                        "foreign_amount": 575.0,
                    },
                ],
            },
        )

    def test_payment_term_compute_method_without_cash_discount_with_cash_rounding(self):
        foreign_currency = self.other_currency
        rate = self.env["res.currency"]._get_conversion_rate(
            foreign_currency,
            self.env.company.currency_id,
            self.env.company,
            "2017-01-01",
        )
        self.assertEqual(rate, 0.5)
        self.pay_term_a.early_pay_discount_computation = "included"
        computed_term_b = self.pay_term_b._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=foreign_currency,
            company=self.env.company,
            tax_amount=75,
            tax_amount_currency=150,
            sign=1,
            untaxed_amount=359.18,
            untaxed_amount_currency=718.35,
            cash_rounding=self.cash_rounding_a,
        )
        self.assertDictEqual(
            {
                "total_amount": computed_term_b.get("total_amount"),
                "discount_balance": computed_term_b.get("discount_balance"),
                "discount_amount_currency": computed_term_b.get(
                    "discount_amount_currency"
                ),
                "line_ids": computed_term_b.get("line_ids"),
            },
            {
                "total_amount": 434.18,
                "discount_balance": 0,
                "discount_amount_currency": 0,
                "line_ids": [
                    {
                        "date": datetime.date(2016, 1, 3),
                        "company_amount": 217.1,
                        "foreign_amount": 434.2,
                    },
                    {
                        "date": datetime.date(2016, 1, 5),
                        "company_amount": 217.08,
                        "foreign_amount": 434.15000000000003,
                    },
                ],
            },
        )
        self.assertAlmostEqual(
            434.18, sum(line["company_amount"] for line in computed_term_b["line_ids"])
        )
        self.assertAlmostEqual(
            868.35, sum(line["foreign_amount"] for line in computed_term_b["line_ids"])
        )

    def test_payment_term_compute_method_early_excluded(self):
        self.pay_term_a.early_pay_discount_computation = "excluded"
        computed_term_a = self.pay_term_a._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.env.company.currency_id,
            company=self.env.company,
            tax_amount=150.0,
            tax_amount_currency=150.0,
            sign=1.0,
            untaxed_amount=1000.0,
            untaxed_amount_currency=1000.0,
        )

        self.assertDictEqual(
            {
                "total_amount": computed_term_a.get("total_amount"),
                "discount_balance": computed_term_a.get("discount_balance"),
                "line_ids": computed_term_a.get("line_ids"),
            },
            {
                "total_amount": 1150.0,
                "discount_balance": 1050.0,
                "line_ids": [
                    {
                        "date": datetime.date(2016, 1, 3),
                        "company_amount": 1150.0,
                        "foreign_amount": 1150.0,
                    }
                ],
            },
        )

    def test_payment_term_residual_amount_on_last_line_with_fixed_amount_multi_currency(
        self,
    ):
        pay_term = self.env["account.payment.term"].create(
            {
                "name": "test_payment_term_residual_amount_on_last_line",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 50,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 50,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 0.02,
                            "value": "fixed",
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )

        computed_term = pay_term._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.other_currency,
            company=self.env.company,
            tax_amount=0.0,
            tax_amount_currency=0.0,
            sign=1.0,
            untaxed_amount=0.04,
            untaxed_amount_currency=0.09,
        )
        self.assertEqual(
            [
                (
                    self.other_currency.round(l["foreign_amount"]),
                    self.company_data["currency"].round(l["company_amount"]),
                )
                for l in computed_term["line_ids"]
            ],
            [(0.045, 0.02), (0.045, 0.02), (0.0, 0.0)],
        )

    def test_payment_term_residual_amount_on_last_line(self):
        pay_term = self.env["account.payment.term"].create(
            {
                "name": "test_payment_term_residual_amount_on_last_line",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 50,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 50,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )

        computed_term = pay_term._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.env.company.currency_id,
            company=self.env.company,
            tax_amount=0.0,
            tax_amount_currency=0.0,
            sign=1.0,
            untaxed_amount=0.03,
            untaxed_amount_currency=0.03,
        )
        self.assertEqual(
            [
                self.env.company.currency_id.round(l["foreign_amount"])
                for l in computed_term["line_ids"]
            ],
            [0.02, 0.01],
        )

    def test_payment_term_last_balance_line_with_fixed(self):
        pay_term = self.env["account.payment.term"].create(
            {
                "name": "test_payment_term_last_balance_line_with_fixed",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 70,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 200,
                            "value": "fixed",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 30,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )

        computed_term = pay_term._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.env.company.currency_id,
            company=self.env.company,
            tax_amount=0.0,
            tax_amount_currency=0.0,
            sign=1.0,
            untaxed_amount=1000.0,
            untaxed_amount_currency=1000.0,
        )

        self.assertEqual(
            [
                self.env.company.currency_id.round(l["foreign_amount"])
                for l in computed_term["line_ids"]
            ],
            [700.0, 200.0, 100.0],
        )

    def test_payment_term_last_balance_line_with_fixed_negative(self):
        pay_term = self.env["account.payment.term"].create(
            {
                "name": "test_payment_term_last_balance_line_with_fixed_negative",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 70,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 500,
                            "value": "fixed",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 30,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )

        computed_term = pay_term._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.env.company.currency_id,
            company=self.env.company,
            tax_amount=0.0,
            tax_amount_currency=0.0,
            sign=1.0,
            untaxed_amount=1000.0,
            untaxed_amount_currency=1000.0,
        )

        self.assertEqual(
            [
                self.env.company.currency_id.round(l["foreign_amount"])
                for l in computed_term["line_ids"]
            ],
            [700.0, 500.0, -200.0],
        )

    def test_payment_term_last_balance_line_with_fixed_negative_fixed(self):
        pay_term = self.env["account.payment.term"].create(
            {
                "name": "test_payment_term_last_balance_line_with_fixed_negative_fixed",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 70,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 500,
                            "value": "fixed",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 30,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 200,
                            "value": "fixed",
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )

        computed_term = pay_term._get_terms(
            date_ref=fields.Date.from_string("2016-01-01"),
            currency=self.env.company.currency_id,
            company=self.env.company,
            tax_amount=0.0,
            tax_amount_currency=0.0,
            sign=1.0,
            untaxed_amount=1000.0,
            untaxed_amount_currency=1000.0,
        )

        self.assertEqual(
            [
                self.env.company.currency_id.round(l["foreign_amount"])
                for l in computed_term["line_ids"]
            ],
            [700.0, 500.0, 300.0, -500.0],
        )

    def test_payment_term_percent_round_calculation(self):
        self.env["account.payment.term"].create(
            {
                "name": "test_payment_term_percent_round_calculation",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 50,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 1.66,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 16.8,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )

    def test_payment_term_days_end_of_month_on_the(self):
        with Form(self.invoice) as basic_case:
            basic_case.invoice_payment_term_id = self.pay_term_days_end_of_month_10
            basic_case.invoice_date = "2023-12-12"

        expected_date_basic_case = (
            self.invoice.line_ids.filtered(
                lambda l: (
                    l.account_id == self.company_data["default_account_receivable"]
                )
            ).mapped("date_maturity"),
        )
        self.assertEqual(
            expected_date_basic_case[0], [fields.Date.from_string("2024-02-10")]
        )

        with Form(self.invoice) as special_case:
            special_case.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            special_case.invoice_date = "2023-12-12"

        expected_date_special_case = (
            self.invoice.line_ids.filtered(
                lambda l: (
                    l.account_id == self.company_data["default_account_receivable"]
                )
            ).mapped("date_maturity"),
        )
        self.assertEqual(
            expected_date_special_case[0], [fields.Date.from_string("2024-02-29")]
        )

    def test_payment_term_labels(self):
        multiple_installment_term = self.env["account.payment.term"].create(
            {
                "name": "test_payment_term_labels",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 40,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 30,
                            "value": "percent",
                            "nb_days": 30,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 30,
                            "value": "percent",
                            "nb_days": 60,
                        }
                    ),
                ],
            }
        )
        immediate_term = self.env["account.payment.term"].create(
            {
                "name": "Immediate",
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 100,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                ],
            }
        )
        invoice = self.init_invoice("out_invoice", products=self.product_a)
        invoice.invoice_payment_term_id = immediate_term
        invoice_terms = invoice.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )
        self.assertEqual(invoice_terms[0].name, False)
        invoice.invoice_payment_term_id = multiple_installment_term
        invoice_terms = invoice.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        ).sorted("date_maturity")
        self.assertEqual(invoice_terms[0].name, "installment #1")
        self.assertEqual(invoice_terms[0].debit, invoice.amount_total * 0.4)
        self.assertEqual(invoice_terms[1].name, "installment #2")
        self.assertEqual(invoice_terms[1].debit, invoice.amount_total * 0.3)
        self.assertEqual(invoice_terms[2].name, "installment #3")
        self.assertEqual(invoice_terms[2].debit, invoice.amount_total * 0.3)

    def test_payment_term_days_end_of_month_nb_days_0(self):
        self.pay_term_days_end_of_month_29.line_ids.nb_days = 0
        self.pay_term_days_end_of_month_31.line_ids.nb_days = 0
        with Form(self.invoice) as case_1:
            case_1.invoice_payment_term_id = self.pay_term_days_end_of_month_29
            case_1.invoice_date = "2024-05-23"

        expected_date_case_1 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_receivable"]
        ).mapped("date_maturity")
        self.assertEqual(expected_date_case_1, [fields.Date.from_string("2024-06-29")])

        with Form(self.invoice) as case_2:
            case_2.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            case_2.invoice_date = "2024-05-23"

        expected_date_case_2 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_receivable"]
        ).mapped("date_maturity")
        self.assertEqual(expected_date_case_2, [fields.Date.from_string("2024-06-30")])

    def test_payment_term_days_end_of_month_nb_days_15(self):
        self.pay_term_days_end_of_month_30.line_ids.nb_days = 15
        self.pay_term_days_end_of_month_31.line_ids.nb_days = 15

        with Form(self.invoice) as case_1:
            case_1.invoice_payment_term_id = self.pay_term_days_end_of_month_30
            case_1.invoice_date = "2024-05-24"

        expected_date_case_1 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_receivable"]
        ).mapped("date_maturity")
        self.assertEqual(expected_date_case_1, [fields.Date.from_string("2024-07-30")])

        with Form(self.invoice) as case_2:
            case_2.invoice_payment_term_id = self.pay_term_days_end_of_month_31
            case_2.invoice_date = "2024-05-23"

        expected_date_case_2 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_receivable"]
        ).mapped("date_maturity")
        self.assertEqual(expected_date_case_2, [fields.Date.from_string("2024-07-31")])

    def test_payment_term_days_end_of_month_days_next_month_0(self):
        with Form(self.invoice) as case_1:
            case_1.invoice_payment_term_id = (
                self.pay_term_days_end_of_month_days_next_month_0
            )
            case_1.invoice_date = "2024-04-22"

        expected_date_case_1 = self.invoice.line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_receivable"]
        ).mapped("date_maturity")
        self.assertEqual(expected_date_case_1, [fields.Date.from_string("2024-05-31")])

    def test_payment_term_multi_company(self):
        user_company = self.env["res.company"].create({"name": "user_company"})
        other_company = self.company_data.get("company")
        self.env.user.write(
            {
                "company_ids": [user_company.id, other_company.id],
                "company_id": user_company.id,
            }
        )
        self.pay_terms_a.company_id = user_company
        self.partner_a.with_company(
            user_company
        ).property_payment_term_id = self.pay_terms_a
        self.partner_a.with_company(other_company).property_payment_term_id = False

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "company_id": other_company.id,
            }
        )
        self.assertFalse(invoice.invoice_payment_term_id)

    def test_is_immediate_true(self):
        self.assertTrue(self.pay_term_today.is_immediate)

    def test_is_immediate_false_nb_days(self):
        self.assertFalse(self.pay_term_net_30_days.is_immediate)

    def test_is_immediate_false_multi_line(self):
        self.assertFalse(self.pay_term_60_days.is_immediate)

    def test_is_immediate_existing_data(self):
        immediate = self.env.ref("account.account_payment_term_immediate")
        self.assertTrue(immediate.is_immediate)

    def test_days_next_month_out_of_range_raises_validation(self):
        term = self.env["account.payment.term"].create({"name": "range days"})
        for bad_value in (-1, 32):
            with self.assertRaises(ValidationError):
                term.line_ids[0].write(
                    {
                        "delay_type": "days_end_of_month_on_the",
                        "days_next_month": bad_value,
                    }
                )

    def test_is_immediate_false_for_deferred_delay_types(self):
        for delay_type in (
            "days_after_end_of_month",
            "days_after_end_of_next_month",
            "days_end_of_month_on_the",
        ):
            term = self.env["account.payment.term"].create(
                {
                    "name": delay_type,
                    "line_ids": [
                        Command.create(
                            {
                                "value": "percent",
                                "value_amount": 100,
                                "nb_days": 0,
                                "delay_type": delay_type,
                            }
                        )
                    ],
                }
            )
            due_date = term.line_ids._get_due_date(datetime.date(2026, 8, 10))
            self.assertNotEqual(due_date, datetime.date(2026, 8, 10))
            self.assertFalse(term.is_immediate)

    def _create_early_discount_invoice(
        self, price, cash_rounding=None, move_type="out_invoice"
    ):
        term = self.env["account.payment.term"].create(
            {
                "name": "2/7 net 30",
                "early_discount": True,
                "discount_percentage": 2.0,
                "discount_days": 7,
                "early_pay_discount_computation": "included",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 100, "nb_days": 30}
                    )
                ],
            }
        )
        return self.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": self.partner_a.id,
                "invoice_date": datetime.date(2026, 3, 1),
                "invoice_payment_term_id": term.id,
                "invoice_cash_rounding_id": cash_rounding.id
                if cash_rounding
                else False,
                "invoice_line_ids": [
                    Command.create(
                        {"name": "x", "quantity": 1, "price_unit": price, "tax_ids": []}
                    )
                ],
            }
        )

    def _payment_term_line(self, move):
        return move.line_ids.filtered(lambda line: line.display_type == "payment_term")

    def test_early_payment_discount_details_match_the_posted_line(self):
        cash_rounding = self.env["account.cash.rounding"].create(
            {
                "name": "nearest 5",
                "rounding": 5.0,
                "strategy": "add_invoice_line",
                "rounding_method": "HALF-UP",
            }
        )
        move = self._create_early_discount_invoice(1234.57, cash_rounding)
        line = self._payment_term_line(move)
        self.assertEqual(
            move._get_early_payment_discount_details(),
            {
                "amount_due": line.discount_amount_currency,
                "date": format_date(self.env, line.discount_date),
            },
        )

    def test_early_payment_discount_details_ignore_the_active_record(self):
        cash_rounding = self.env["account.cash.rounding"].create(
            {
                "name": "nearest 5",
                "rounding": 5.0,
                "strategy": "add_invoice_line",
                "rounding_method": "HALF-UP",
            }
        )
        other = self._create_early_discount_invoice(1234.57, cash_rounding)
        move = self._create_early_discount_invoice(99.0)
        printed_alone = move.with_context(
            active_model="account.move", active_id=move.id
        )._get_early_payment_discount_details()
        printed_in_batch = move.with_context(
            active_model="account.move", active_id=other.id
        )._get_early_payment_discount_details()
        self.assertEqual(printed_in_batch, printed_alone)
        self.assertEqual(printed_alone["amount_due"], 97.02)

    def test_early_payment_discount_details_are_positive_on_a_vendor_bill(self):
        move = self._create_early_discount_invoice(1000.0, move_type="in_invoice")
        self.assertEqual(self._payment_term_line(move).discount_amount_currency, -980.0)
        self.assertEqual(
            move._get_early_payment_discount_details()["amount_due"], 980.0
        )

    def test_percent_sum_is_checked_on_a_direct_line_write(self):
        with self.assertRaises(ValidationError):
            self.pay_term_today.line_ids.write({"value_amount": 50.0})
            self.pay_term_today.line_ids.flush_recordset()

    def test_switching_a_line_to_fixed_clears_the_auto_filled_amount(self):
        term_form = Form(self.env["account.payment.term"])
        term_form.name = "fixed first line"
        with term_form.line_ids.edit(0) as line:
            self.assertEqual(line.value_amount, 100.0)
            line.value = "fixed"
            self.assertEqual(line.value_amount, 0.0)
        with term_form.line_ids.new() as line:
            line.value_amount = 100
            line.nb_days = 30
        term = term_form.save()
        self.assertEqual(
            [(line.value, line.value_amount) for line in term.line_ids],
            [("fixed", 0.0), ("percent", 100.0)],
        )

    def test_company_change_keeps_a_manual_tax_reduction(self):
        term = self.pay_term_today
        term.write(
            {"early_discount": True, "early_pay_discount_computation": "excluded"}
        )
        term.write({"company_id": self.env.company.id})
        term.flush_recordset()
        self.assertEqual(term.early_pay_discount_computation, "excluded")

    def test_nb_days_chains_from_the_previous_line(self):
        term = self.env["account.payment.term"].create(
            {
                "name": "chained days",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 40, "nb_days": 10}
                    ),
                    Command.create({"value": "percent", "value_amount": 30}),
                    Command.create({"value": "percent", "value_amount": 30}),
                ],
            }
        )
        self.assertEqual(term.line_ids.mapped("nb_days"), [10, 40, 70])

    def test_example_fields_read_their_context_keys(self):
        model = self.env["account.payment.term"].with_context(
            example_amount=777.0, example_date="2030-01-01"
        )
        self.assertEqual(
            model.default_get(["example_amount", "example_date"]),
            {"example_amount": 777.0, "example_date": datetime.date(2030, 1, 1)},
        )

    def test_zero_total_invoice_has_no_installment_amounts(self):
        term = self.env["account.payment.term"].create(
            {
                "name": "fixed then balance",
                "line_ids": [
                    Command.create(
                        {"value": "fixed", "value_amount": 100, "nb_days": 0}
                    ),
                    Command.create(
                        {"value": "percent", "value_amount": 100, "nb_days": 30}
                    ),
                ],
            }
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": datetime.date(2026, 3, 1),
                "invoice_payment_term_id": term.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "free",
                            "quantity": 1,
                            "price_unit": 0.0,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        self.assertEqual(
            self._payment_term_line(move).mapped("amount_currency"), [0.0, 0.0]
        )

    def test_example_preview_follows_the_delay_type(self):
        term = self.env["account.payment.term"].create(
            {
                "name": "preview",
                "example_date": "2026-03-10",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 100, "nb_days": 0}
                    )
                ],
            }
        )
        self.assertIn("03/10/2026", term.example_preview)
        term.line_ids.delay_type = "days_after_end_of_next_month"
        self.assertIn("04/30/2026", term.example_preview)
        term.line_ids.write(
            {"delay_type": "days_end_of_month_on_the", "days_next_month": 20}
        )
        self.assertIn("04/20/2026", term.example_preview)

    def test_line_sequence_decides_which_line_carries_the_balance(self):
        term = self.env["account.payment.term"].create(
            {
                "name": "resequenced",
                "line_ids": [
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 30,
                            "nb_days": 0,
                            "sequence": 10,
                        }
                    ),
                    Command.create(
                        {
                            "value": "percent",
                            "value_amount": 70,
                            "nb_days": 30,
                            "sequence": 20,
                        }
                    ),
                ],
            }
        )
        self.assertEqual(term.line_ids.mapped("value_amount"), [30.0, 70.0])
        term.line_ids[0].sequence = 30
        term.invalidate_recordset(["line_ids"])
        self.assertEqual(term.line_ids.mapped("value_amount"), [70.0, 30.0])

    def _discount_term(self, scheme):
        return self.env["account.payment.term"].create(
            {
                "name": scheme,
                "early_discount": True,
                "discount_percentage": 10.0,
                "discount_days": 7,
                "early_pay_discount_computation": scheme,
                "example_date": "2026-03-10",
                "line_ids": [
                    Command.create(
                        {"value": "percent", "value_amount": 100, "nb_days": 30}
                    )
                ],
            }
        )

    def _preview_discount(self, term, **context):
        term.invalidate_recordset()
        return term.with_context(**context).example_preview_discount

    def test_example_preview_discount_needs_tax_to_show_the_scheme(self):
        schemes = ("included", "excluded", "mixed")
        without_tax = {
            scheme: self._preview_discount(self._discount_term(scheme))
            for scheme in schemes
        }
        self.assertEqual(
            len(set(without_tax.values())),
            1,
            "a tax-free example cannot distinguish the schemes and must not pretend to",
        )
        with_tax = {
            scheme: self._preview_discount(
                self._discount_term(scheme),
                example_amount=1150.0,
                example_tax_amount=150.0,
            )
            for scheme in schemes
        }
        self.assertIn("1,035.00", with_tax["included"])
        self.assertIn("1,050.00", with_tax["excluded"])
        self.assertIn("1,050.00", with_tax["mixed"])

    def test_example_preview_discount_matches_the_invoice_it_opens_from(self):
        for scheme in ("included", "excluded", "mixed"):
            term = self._discount_term(scheme)
            move = self.env["account.move"].create(
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": datetime.date(2026, 3, 10),
                    "invoice_payment_term_id": term.id,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "x",
                                "quantity": 1,
                                "price_unit": 1000,
                                "tax_ids": [Command.set(self.tax_sale_a.ids)],
                            }
                        )
                    ],
                }
            )
            posted = self._payment_term_line(move).discount_amount_currency
            totals = move.tax_totals
            preview = self._preview_discount(
                term,
                example_date=move.invoice_date,
                example_amount=totals["total_amount_currency"],
                example_tax_amount=totals["tax_amount_currency"],
            )
            rendered = str(preview).replace("&nbsp;", "\xa0")
            self.assertIn(
                formatLang(self.env, posted, currency_obj=move.currency_id),
                rendered,
                f"the {scheme} preview must quote what the invoice posts",
            )
