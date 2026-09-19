import json
from contextlib import closing
from unittest.mock import patch

from psycopg.errors import CheckViolation

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import Form, tagged, users
from odoo.tools import SQL

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountMoveReconcile(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.receivable_account = cls.company_data["default_account_receivable"]
        cls.payable_account = cls.company_data["default_account_payable"]
        cls.expense_account = cls.company_data["default_account_expense"]
        cls.revenue_account = cls.company_data["default_account_revenue"]

        cls.extra_receivable_account_1 = cls.copy_account(cls.receivable_account)
        cls.extra_receivable_account_2 = cls.copy_account(cls.receivable_account)
        cls.extra_payable_account_1 = cls.copy_account(
            cls.company_data["default_account_payable"]
        )
        cls.extra_payable_account_2 = cls.copy_account(
            cls.company_data["default_account_payable"]
        )

        cls.exch_income_account = (
            cls.env.company.account_config_id.income_currency_exchange_account_id
        )
        cls.exch_expense_account = (
            cls.env.company.account_config_id.expense_currency_exchange_account_id
        )

        cls.other_currency = cls.setup_other_currency("EUR", rounding=0.001)
        cls.other_currency_2 = cls.setup_other_currency(
            "CAD", rates=[("2016-01-01", 6.0), ("2017-01-01", 4.0)]
        )
        cls.other_currency_3 = cls.setup_other_currency(
            "XAF", rates=[("2016-01-01", 0.0001), ("2017-01-01", 0.00001)]
        )

        cls.cash_basis_base_account = cls.env["account.account"].create(
            {
                "code": "cash.basis.base.account",
                "name": "cash_basis_base_account",
                "account_type": "income",
            }
        )
        cls.company_data[
            "company"
        ].account_config_id.account_cash_basis_base_account_id = (
            cls.cash_basis_base_account
        )

        cls.cash_basis_transfer_account = cls.env["account.account"].create(
            {
                "code": "cash.basis.transfer.account",
                "name": "cash_basis_transfer_account",
                "account_type": "income",
                "reconcile": True,
            }
        )

        cls.tax_account_1 = cls.env["account.account"].create(
            {
                "code": "tax.account.1",
                "name": "tax_account_1",
                "account_type": "income",
            }
        )

        cls.tax_account_2 = cls.env["account.account"].create(
            {
                "code": "tax.account.2",
                "name": "tax_account_2",
                "account_type": "income",
            }
        )

        cls.fake_country = cls.env["res.country"].create(
            {
                "name": "The Island of the Fly",
                "code": "YY",
            }
        )

        cls.tax_tags = cls.env["account.account.tag"].create(
            [
                {
                    "name": "tax_tag_%s" % str(i),
                    "applicability": "taxes",
                    "country_id": cls.company_data[
                        "company"
                    ].account_config_id.account_fiscal_country_id.id,
                }
                for i in range(10)
            ]
        )

        cls.cash_basis_tax_a_third_amount = cls.env["account.tax"].create(
            {
                "name": "tax_1",
                "amount": 33.3333,
                "company_ids": [Command.set(cls.company_data["company"].ids)],
                "cash_basis_transition_account_id": cls.cash_basis_transfer_account.id,
                "tax_exigibility": "on_payment",
                "invoice_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "repartition_type": "base",
                            "tag_ids": [(6, 0, cls.tax_tags[0].ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "repartition_type": "tax",
                            "account_id": cls.tax_account_1.id,
                            "tag_ids": [(6, 0, cls.tax_tags[1].ids)],
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "repartition_type": "base",
                            "tag_ids": [(6, 0, cls.tax_tags[2].ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "repartition_type": "tax",
                            "account_id": cls.tax_account_1.id,
                            "tag_ids": [(6, 0, cls.tax_tags[3].ids)],
                        },
                    ),
                ],
            }
        )

        cls.cash_basis_tax_tiny_amount = cls.env["account.tax"].create(
            {
                "name": "cash_basis_tax_tiny_amount",
                "amount": 0.0001,
                "company_ids": [Command.set(cls.company_data["company"].ids)],
                "cash_basis_transition_account_id": cls.cash_basis_transfer_account.id,
                "tax_exigibility": "on_payment",
                "invoice_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "repartition_type": "base",
                            "tag_ids": [(6, 0, cls.tax_tags[4].ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "repartition_type": "tax",
                            "account_id": cls.tax_account_2.id,
                            "tag_ids": [(6, 0, cls.tax_tags[5].ids)],
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "repartition_type": "base",
                            "tag_ids": [(6, 0, cls.tax_tags[6].ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "repartition_type": "tax",
                            "account_id": cls.tax_account_2.id,
                            "tag_ids": [(6, 0, cls.tax_tags[7].ids)],
                        },
                    ),
                ],
            }
        )

        cls.cash_basis_tax_tiny_amount_2 = cls.env["account.tax"].create(
            {
                "name": "cash_basis_tax_tiny_amount_2",
                "amount": 0.005,
                "company_ids": [Command.set(cls.company_data["company"].ids)],
                "cash_basis_transition_account_id": cls.cash_basis_transfer_account.id,
                "tax_exigibility": "on_payment",
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "repartition_type": "base",
                            "tag_ids": [Command.set(cls.tax_tags[8].ids)],
                        }
                    ),
                    Command.create(
                        {
                            "repartition_type": "tax",
                            "account_id": cls.tax_account_1.id,
                            "tag_ids": [Command.set(cls.tax_tags[9].ids)],
                        }
                    ),
                ],
            }
        )

    def assertFullReconcile(self, full_reconcile, lines):
        partials = lines.mapped("matched_debit_ids") + lines.mapped(
            "matched_credit_ids"
        )

        self.assertEqual(set(full_reconcile.partial_reconcile_ids), set(partials))
        self.assertEqual(set(full_reconcile.reconciled_line_ids), set(lines))

        self.assertRecordValues(
            lines,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": bool(line.account_id.reconcile),
                }
                for line in lines
            ],
        )

    def assertFullReconcileAccount(self, full_reconcile, account):
        self.assertFullReconcile(
            full_reconcile,
            self.env["account.move.line"].search([("account_id", "=", account.id)]),
        )

    def assertAmountsGroupByAccount(self, amount_per_account):
        expected_values = {
            account.id: (account, balance, amount_currency)
            for account, balance, amount_currency in amount_per_account
        }

        if not expected_values:
            return

        self.cr.execute(
            """
            SELECT
                line.account_id,
                COALESCE(SUM(line.balance), 0.0)            AS total_balance,
                COALESCE(SUM(line.amount_currency), 0.0)    AS total_amount_currency
            FROM account_move_line line
            WHERE line.account_id = ANY(%s)
            GROUP BY line.account_id
        """,
            [list(expected_values.keys())],
        )
        for account_id, total_balance, total_amount_currency in self.cr.fetchall():
            account, expected_balance, expected_amount_currency = expected_values[
                account_id
            ]
            self.assertEqual(
                total_balance,
                expected_balance,
                "Balance of %s is incorrect" % account.name,
            )
            self.assertEqual(
                total_amount_currency,
                expected_amount_currency,
                "Amount currency of %s is incorrect" % account.name,
            )

    def create_move_payment(self, move, payment_amount, with_outstanding_account=False):
        return (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=move.ids,
            )
            .create(
                {
                    "amount": payment_amount,
                    "payment_channel_id": self.company_data["default_journal_bank"]
                    .inbound_payment_channel_ids.filtered_domain(
                        [
                            (
                                "payment_account_id",
                                "!=" if with_outstanding_account else "=",
                                False,
                            ),
                        ]
                    )[0]
                    .id,
                }
            )
            ._create_payments()
        )

    def _get_partials(self, amls):
        return (amls.matched_debit_ids | amls.matched_credit_ids).sorted()

    def _get_caba_moves(self, moves):
        return moves.search([("tax_cash_basis_origin_move_id", "in", moves.ids)])

    @users("simple_accountman")
    def test_full_reconcile_bunch_lines(self):
        comp_curr = self.company_data["currency"]
        foreign_curr1 = self.other_currency
        foreign_curr2 = self.other_currency_2

        line_1 = self.create_line_for_reconciliation(
            1000.0, 1000.0, comp_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -300.0, -300.0, comp_curr, "2016-01-01"
        )
        line_3 = self.create_line_for_reconciliation(
            -400.0, -400.0, comp_curr, "2016-01-01"
        )
        line_4 = self.create_line_for_reconciliation(
            -500.0, -500.0, comp_curr, "2016-01-01"
        )
        line_5 = self.create_line_for_reconciliation(
            200.0, 200.0, comp_curr, "2016-01-01"
        )
        comp_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        line_1 = self.create_line_for_reconciliation(
            1200.0, 3600.0, foreign_curr1, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -240.0, -480.0, foreign_curr1, "2017-01-01"
        )
        line_3 = self.create_line_for_reconciliation(
            -720.0, -1440.0, foreign_curr1, "2017-01-01"
        )
        line_4 = self.create_line_for_reconciliation(
            -1020.0, -2040.0, foreign_curr1, "2017-01-01"
        )
        line_5 = self.create_line_for_reconciliation(
            120.0, 360.0, foreign_curr1, "2016-01-01"
        )
        same_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        line_1 = self.create_line_for_reconciliation(
            1200.0, 3600.0, foreign_curr1, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            780.0, 2340.0, foreign_curr1, "2016-01-01"
        )
        line_3 = self.create_line_for_reconciliation(
            -240.0, -960.0, foreign_curr2, "2017-01-01"
        )
        line_4 = self.create_line_for_reconciliation(
            -720.0, -2880.0, foreign_curr2, "2017-01-01"
        )
        line_5 = self.create_line_for_reconciliation(
            -1020.0, -4080.0, foreign_curr2, "2017-01-01"
        )
        multi_curr_batch = line_1 + line_2 + line_3 + line_4 + line_5

        for batch, sub_test_name in (
            (comp_curr_batch, "Batch in company currency"),
            (same_curr_batch, "Batch in foreign currency"),
            (multi_curr_batch, "Batch with multiple currencies"),
            (comp_curr_batch + same_curr_batch + multi_curr_batch, "All batches"),
        ):
            with self.subTest(sub_test_name=sub_test_name):
                batch.reconcile()
                self.assertTrue(batch.full_reconcile_id)
                self.assertRecordValues(
                    batch,
                    [
                        {
                            "amount_residual": 0.0,
                            "amount_residual_currency": 0.0,
                            "reconciled": True,
                        }
                    ]
                    * len(batch),
                )
                batch.remove_move_reconcile()

    def test_reconcile_lines_multiple_in_foreign_currency(self):
        currency = self.other_currency

        rates = (1 / 3, 1 / 2)
        for rate1 in rates:
            for rate2 in rates:
                for rate3 in rates:
                    with self.subTest(rate1=rate1, rate2=rate2, rate3=rate3):
                        line_1 = self.create_line_for_reconciliation(
                            120.0 * rate1, 120.0, currency, "2017-01-01"
                        )
                        line_2 = self.create_line_for_reconciliation(
                            120.0 * rate2, 120.0, currency, "2017-01-01"
                        )
                        line_3 = self.create_line_for_reconciliation(
                            -240.0 * rate3, -240.0, currency, "2017-01-01"
                        )

                        (line_1 + line_2 + line_3).reconcile()
                        self.assertTrue(line_1.full_reconcile_id)

    def test_reverse_exchange_difference(self):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        for line1_vals, line2_vals in (
            (
                (60.0, 120.0, foreign_curr, "2017-01-01"),
                (-40.0, -120.0, foreign_curr, "2016-01-01"),
            ),
            (
                (-60.0, -120.0, foreign_curr, "2017-01-01"),
                (40.0, 120.0, foreign_curr, "2016-01-01"),
            ),
            (
                (60.0, 60.0, comp_curr, "2017-01-01"),
                (-40.0, -120.0, foreign_curr, "2016-01-01"),
            ),
            (
                (-60.0, -60.0, comp_curr, "2017-01-01"),
                (40.0, 120.0, foreign_curr, "2016-01-01"),
            ),
        ):
            line1 = self.create_line_for_reconciliation(*line1_vals)
            line2 = self.create_line_for_reconciliation(*line2_vals)
            with self.subTest(line1_vals=line1_vals, line2_vals=line2_vals):
                (line1 + line2).reconcile()

                partials = self._get_partials(line1 + line2)
                exchange_diff = partials.exchange_move_id
                self.assertTrue(exchange_diff)

                line1.remove_move_reconcile()
                reverse_exchange_diff_lines = (
                    exchange_diff.line_ids.matched_debit_ids.debit_move_id
                    + exchange_diff.line_ids.matched_credit_ids.credit_move_id
                )
                reverse_exchange_diff = reverse_exchange_diff_lines.move_id
                self.assertTrue(reverse_exchange_diff)

                self.assertRecordValues(
                    exchange_diff.line_ids + reverse_exchange_diff.line_ids,
                    [
                        {"reconciled": True},
                        {"reconciled": False},
                        {"reconciled": True},
                        {"reconciled": False},
                    ],
                )

    def test_invoice_draft_fully_paid_if_zero(self):
        zero_invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": fields.Date.from_string("2019-01-01"),
                "invoice_line_ids": [Command.create({"name": "Nope", "price_unit": 0})],
            }
        )
        payment_term_line = zero_invoice.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        )
        self.assertRecordValues(
            zero_invoice,
            [
                {
                    "state": "draft",
                    "payment_state": "not_paid",
                    "amount_total": 0.0,
                }
            ],
        )
        self.assertTrue(payment_term_line.reconciled)

        zero_invoice.action_post()
        self.assertRecordValues(
            zero_invoice,
            [
                {
                    "state": "posted",
                    "payment_state": "paid",
                    "amount_total": 0.0,
                }
            ],
        )
        self.assertTrue(payment_term_line.reconciled)

    def test_reconcile_lines_corner_case_1_zero_balance_same_foreign_currency(self):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(0.0, -0.02, currency, "2017-01-01")
        line_2 = self.create_line_for_reconciliation(0.0, 0.01, currency, "2017-01-01")
        (line_1 + line_2).reconcile()

        self.assertFalse(
            line_1.full_reconcile_id + line_2.full_reconcile_id,
            "The reconciliation should not be considered full, as 0.01 still remain open in foreign currency.",
        )

        line_3 = self.create_line_for_reconciliation(0.0, 0.01, currency, "2017-01-01")
        (line_1 + line_3).reconcile()

        self.assertTrue(line_1.full_reconcile_id)
        self.assertEqual(line_1.full_reconcile_id, line_2.full_reconcile_id)
        self.assertEqual(line_2.full_reconcile_id, line_3.full_reconcile_id)

    def test_reconcile_lines_corner_case_1_zero_balance_different_foreign_currency(
        self,
    ):
        currency_1 = self.other_currency
        currency_2 = self.setup_other_currency("CHF")

        line_1 = self.create_line_for_reconciliation(
            0.0, -0.01, currency_1, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            0.0, 0.02, currency_2, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertFalse(partials)

    def test_reconcile_lines_corner_case_2_zero_amount_currency_same_foreign_currency(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(-0.01, 0.0, currency, "2017-01-01")
        line_2 = self.create_line_for_reconciliation(0.02, 0.0, currency, "2016-01-01")
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 0.01,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.01,
                    "amount_residual_currency": 0.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_lines_corner_case_3_zero_balance_one_foreign_currency(self):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -0.01, -0.01, comp_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            0.0, 0.03, foreign_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 0.0,
                    "debit_amount_currency": 0.02,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 0.01,
                    "debit_amount_currency": 0.01,
                    "credit_amount_currency": 0.01,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "amount_currency": 0.01,
                    "currency_id": comp_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "amount_currency": -0.01,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.01,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_lines_corner_case_4_zero_amount_currency_multiple_currencies(
        self,
    ):
        foreign_curr1 = self.other_currency
        foreign_curr2 = self.other_currency_2

        line_1 = self.create_line_for_reconciliation(
            -0.01, 0.0, foreign_curr2, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            0.01, 0.03, foreign_curr1, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 0.01,
                    "debit_amount_currency": 0.03,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                    "exchange_move_id": None,
                }
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_lines_corner_case_5_zero_balance_in_one_line_same_foreign_currency(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(-0.06, 0.0, currency, "2017-01-01")
        line_2 = self.create_line_for_reconciliation(0.12, 0.24, currency, "2017-01-01")
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 0.06,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.06,
                    "amount_residual_currency": 0.24,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_expense_partial_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            60.0, 120.0, currency, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -80.0, -240.0, currency, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": -40.0,
                    "amount_residual_currency": -120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_income_partial_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            40.0, 120.0, currency, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -120.0, -240.0, currency, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_2.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": -60.0,
                    "amount_residual_currency": -120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_expense_partial_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -40.0, -120.0, currency, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            120.0, 240.0, currency, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 60.0,
                    "amount_residual_currency": 120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_income_partial_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -60.0, -120.0, currency, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            80.0, 240.0, currency, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 40.0,
                    "amount_residual_currency": 120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_expense_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            60.0, 120.0, foreign_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -80.0, -80.0, comp_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": -40.0,
                    "amount_residual_currency": -40.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_expense_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            60.0, 60.0, comp_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -80.0, -240.0, foreign_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": -40.0,
                    "amount_residual_currency": -120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_income_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            40.0, 120.0, foreign_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -120.0, -120.0, comp_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_2.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": -60.0,
                    "amount_residual_currency": -60.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_income_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            40.0, 40.0, comp_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -120.0, -240.0, foreign_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_2.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": -60.0,
                    "amount_residual_currency": -120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_expense_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -40.0, -120.0, foreign_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            120.0, 120.0, comp_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 60.0,
                    "amount_residual_currency": 60.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_expense_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -40.0, -40.0, comp_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            120.0, 240.0, foreign_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 60.0,
                    "amount_residual_currency": 120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_income_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -60.0, -60.0, comp_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            80.0, 240.0, foreign_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 40.0,
                    "amount_residual_currency": 120.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_income_partial_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -60.0, -120.0, foreign_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            80.0, 80.0, comp_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 40.0,
                    "amount_residual_currency": 40.0,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_one_foreign_currency_fallback_company_currency(self):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency_3
        foreign_curr.rounding = 0.001

        line_1 = self.create_line_for_reconciliation(
            -10.0, -10.0, comp_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            1000000.0, 100.0, foreign_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 10.0,
                    "debit_amount_currency": 0.001,
                    "credit_amount_currency": 10.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                }
            ],
        )
        self.assertFalse(partials.exchange_move_id)
        self.assertRecordValues(
            line_1 + line_2,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 999990.0,
                    "amount_residual_currency": 99.999,
                    "reconciled": False,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_expense_full_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            60.0, 120.0, currency, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -40.0, -120.0, currency, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_debit_income_full_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            40.0, 120.0, currency, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -60.0, -120.0, currency, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_2.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_expense_full_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -40.0, -120.0, currency, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            60.0, 120.0, currency, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_same_foreign_currency_credit_income_full_payment(
        self,
    ):
        currency = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -60.0, -120.0, currency, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            40.0, 120.0, currency, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": currency.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            line_1 + line_2,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_expense_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            60.0, 120.0, foreign_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -40.0, -40.0, comp_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_expense_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            60.0, 60.0, comp_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -40.0, -120.0, foreign_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_debit_income_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            40.0, 120.0, foreign_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -60.0, -60.0, comp_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_2.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_debit_income_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            40.0, 40.0, comp_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -60.0, -120.0, foreign_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_2.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_expense_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -40.0, -40.0, comp_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            60.0, 120.0, foreign_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_expense_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -40.0, -120.0, foreign_curr, "2016-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            60.0, 60.0, comp_curr, "2017-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": partials.exchange_move_id.line_ids[0].id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_debit_foreign_currency_credit_income_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -60.0, -60.0, comp_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            40.0, 120.0, foreign_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 120.0,
                    "credit_amount_currency": 40.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 20.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 20.0,
                    "currency_id": comp_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": -20.0,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_exchange_difference_on_partial_one_credit_foreign_currency_credit_income_full_payment(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -60.0, -120.0, foreign_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            40.0, 40.0, comp_curr, "2016-01-01"
        )
        amls = line_1 + line_2

        amls.reconcile()
        partials = self._get_partials(amls)
        full_reconcile = amls.full_reconcile_id

        self.assertTrue(full_reconcile)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 40.0,
                    "debit_amount_currency": 40.0,
                    "credit_amount_currency": 120.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": line_1.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2017-01-31")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 20.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 20.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_invoice_company_curr_payment_foreign_curr(self):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2017-01-01",
                "date": "2017-01-01",
                "partner_id": self.partner_a.id,
                "currency_id": comp_curr.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 60.0,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        payment = (
            self.env["account.payment.register"]
            .with_context(active_model=invoice._name, active_ids=invoice.ids)
            .create(
                {
                    "payment_date": "2016-01-01",
                    "amount": 90.0,
                    "currency_id": foreign_curr.id,
                }
            )
            ._create_payments()
        )

        lines = (invoice + payment.move_id).line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        self.assertRecordValues(
            lines,
            [
                {
                    "amount_residual": 30.0,
                    "amount_residual_currency": 30.0,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reverse_with_multiple_lines(self):
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 1200.0,
                            "credit": 0.0,
                            "amount_currency": 3600.0,
                            "currency_id": self.other_currency.id,
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 200.0,
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 400.0,
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 600.0,
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                        },
                    ),
                ],
            }
        )

        move.action_post()

        lines_to_reconcile = move.line_ids.filtered(
            lambda x: (
                (
                    x.account_id.reconcile
                    or x.account_id.account_type
                    in ("asset_cash", "liability_credit_card")
                )
                and not x.reconciled
            )
        )

        self.assertRecordValues(
            lines_to_reconcile,
            [
                {"debit": 1200.0, "credit": 0.0, "reconciled": False},
                {"debit": 0.0, "credit": 200.0, "reconciled": False},
                {"debit": 0.0, "credit": 400.0, "reconciled": False},
                {"debit": 0.0, "credit": 600.0, "reconciled": False},
            ],
        )

        reversed_move = move._reverse_moves(cancel=True)

        reversed_lines = reversed_move.line_ids.filtered(
            lambda x: (
                x.account_id.reconcile
                or x.account_id.account_type in ("asset_cash", "liability_credit_card")
            )
        )

        self.assertRecordValues(
            reversed_lines,
            [
                {"debit": 0.0, "credit": 1200.0, "reconciled": True},
                {"debit": 200.0, "credit": 0.0, "reconciled": True},
                {"debit": 400.0, "credit": 0.0, "reconciled": True},
                {"debit": 600.0, "credit": 0.0, "reconciled": True},
            ],
        )

        self.assertTrue(all(line.full_reconcile_id for line in reversed_lines))

    def test_reconcile_foreign_currency_rounding_issue(self):
        comp_curr = self.company_data["currency"]
        foreign_currency = self.env["res.currency"].create(
            {
                "name": "Bread",
                "symbol": "🍞",
                "rounding": 0.01,
                "rate_ids": [
                    Command.create({"name": "2019-06-01", "rate": 0.052972554919}),
                ],
            }
        )

        non_rec_pay_account = self.company_data["default_account_revenue"].copy()
        non_rec_pay_account.reconcile = True
        self.assertFalse(
            non_rec_pay_account.account_type
            in ("asset_receivable", "liability_payable")
        )
        rec_pay_account = self.company_data["default_account_receivable"].copy()
        self.assertTrue(rec_pay_account.reconcile)
        self.assertTrue(
            rec_pay_account.account_type in ("asset_receivable", "liability_payable")
        )

        for sign, reco_account in [
            (-1, non_rec_pay_account),
            (1, non_rec_pay_account),
            (-1, rec_pay_account),
            (1, rec_pay_account),
        ]:
            with self.subTest(
                sub_test_name=f"sign: {sign}, reco_account: {reco_account.name}"
            ):
                line_1 = self.create_line_for_reconciliation(
                    balance=sign * 377554.0,
                    amount_currency=sign * 20000.0,
                    currency=foreign_currency,
                    move_date="2019-06-01",
                    account_1=reco_account,
                )
                line_2 = self.create_line_for_reconciliation(
                    balance=-sign * 372239.38,
                    amount_currency=-sign * 372239.38,
                    currency=comp_curr,
                    move_date="2019-06-01",
                    account_1=reco_account,
                )
                line_3 = self.create_line_for_reconciliation(
                    balance=-sign * 5314.62,
                    amount_currency=-sign * 281.53,
                    currency=foreign_currency,
                    move_date="2019-06-01",
                    account_1=reco_account,
                )
                amls = line_1 + line_2 + line_3
                amls.reconcile()

                full_reconcile = amls.full_reconcile_id
                self.assertTrue(full_reconcile)
                self.assertTrue(
                    all(line.full_reconcile_id == full_reconcile for line in amls)
                )
                self.assertRecordValues(
                    amls,
                    [
                        {
                            "amount_residual": 0.0,
                            "amount_residual_currency": 0.0,
                            "reconciled": True,
                        }
                    ]
                    * len(amls),
                )

                partials = self._get_partials(amls)
                if sign == 1:
                    expected_partials = [
                        {
                            "amount": 5314.62,
                            "debit_amount_currency": 281.53,
                            "credit_amount_currency": 281.53,
                            "debit_move_id": line_1.id,
                            "credit_move_id": line_3.id,
                        },
                        {
                            "amount": 372239.38,
                            "debit_amount_currency": 19718.47,
                            "credit_amount_currency": 372239.38,
                            "debit_move_id": line_1.id,
                            "credit_move_id": line_2.id,
                        },
                    ]
                else:
                    expected_partials = [
                        {
                            "amount": 5314.62,
                            "debit_amount_currency": 281.53,
                            "credit_amount_currency": 281.53,
                            "debit_move_id": line_3.id,
                            "credit_move_id": line_1.id,
                        },
                        {
                            "amount": 372239.38,
                            "debit_amount_currency": 372239.38,
                            "credit_amount_currency": 19718.47,
                            "debit_move_id": line_2.id,
                            "credit_move_id": line_1.id,
                        },
                    ]
                self.assertRecordValues(partials.sorted("amount"), expected_partials)

    def test_reconcile_partial_exchange_rounding_issue(self):
        comp_curr = self.company_data["currency"]
        foreign_currency = self.env["res.currency"].create(
            {
                "name": "Bread",
                "symbol": "🍞",
                "rounding": 0.01,
                "rate_ids": [
                    Command.create({"name": "2019-06-01", "rate": 0.052972554919}),
                ],
            }
        )

        non_rec_pay_account = self.company_data["default_account_revenue"].copy()
        non_rec_pay_account.reconcile = True
        self.assertFalse(
            non_rec_pay_account.account_type
            in ("asset_receivable", "liability_payable")
        )
        rec_pay_account = self.company_data["default_account_receivable"].copy()
        self.assertTrue(rec_pay_account.reconcile)
        self.assertTrue(
            rec_pay_account.account_type in ("asset_receivable", "liability_payable")
        )

        for sign, reco_account in [
            (-1, non_rec_pay_account),
            (1, non_rec_pay_account),
            (-1, rec_pay_account),
            (1, rec_pay_account),
        ]:
            with self.subTest(
                sub_test_name=f"sign: {sign}, reco_account: {reco_account.name}"
            ):
                line_1 = self.create_line_for_reconciliation(
                    balance=sign * 377554.0,
                    amount_currency=sign * 20000.0,
                    currency=foreign_currency,
                    move_date="2019-06-01",
                    account_1=reco_account,
                )
                line_2 = self.create_line_for_reconciliation(
                    balance=-sign * 372239.38,
                    amount_currency=-sign * 372239.38,
                    currency=comp_curr,
                    move_date="2019-06-01",
                    account_1=reco_account,
                )
                amls = line_1 + line_2
                amls.reconcile()

                full_reconcile = amls.full_reconcile_id
                self.assertFalse(full_reconcile)

                partials = self._get_partials(amls)
                if sign == 1:
                    expected_partials = [
                        {
                            "amount": 372239.38,
                            "debit_amount_currency": 19718.47,
                            "credit_amount_currency": 372239.38,
                            "debit_move_id": line_1.id,
                            "credit_move_id": line_2.id,
                        },
                    ]
                else:
                    expected_partials = [
                        {
                            "amount": 372239.38,
                            "debit_amount_currency": 372239.38,
                            "credit_amount_currency": 19718.47,
                            "debit_move_id": line_2.id,
                            "credit_move_id": line_1.id,
                        },
                    ]
                self.assertRecordValues(partials.sorted("amount"), expected_partials)

    def test_full_reconcile_foreign_currency_rounding_difference_credit_larger(self):
        foreign_currency = self.env["res.currency"].create(
            {
                "name": "Bread",
                "symbol": "🍞",
                "rounding": 0.01,
                "rate_ids": [
                    Command.create({"name": "2019-06-01", "rate": 0.648587}),
                ],
            }
        )

        rec_pay_account = self.company_data["default_account_receivable"].copy()
        self.assertTrue(rec_pay_account.reconcile)

        line_1 = self.create_line_for_reconciliation(
            -44.41, -28.8, foreign_currency, "2019-06-01", rec_pay_account
        )
        line_2 = self.create_line_for_reconciliation(
            44.4, 28.8, foreign_currency, "2019-06-01", rec_pay_account
        )
        amls = line_1 + line_2
        amls.reconcile()

        full_reconcile = amls.full_reconcile_id
        self.assertTrue(full_reconcile)

        partials = self._get_partials(amls)
        exchange_move = partials.exchange_move_id

        self.assertRecordValues(
            exchange_move.line_ids,
            [
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "account_id": line_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.sorted("amount"),
            [
                {
                    "amount": 0.01,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": exchange_move.line_ids.sorted("balance")[1].id,
                    "credit_move_id": line_1.id,
                },
                {
                    "amount": 44.40,
                    "debit_amount_currency": 28.8,
                    "credit_amount_currency": 28.8,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
            ],
        )

    def test_full_reconcile_foreign_currency_rounding_difference_debit_larger(self):
        foreign_currency = self.env["res.currency"].create(
            {
                "name": "Bread",
                "symbol": "🍞",
                "rounding": 0.01,
                "rate_ids": [
                    Command.create({"name": "2019-06-01", "rate": 0.648587}),
                ],
            }
        )

        rec_pay_account = self.company_data["default_account_receivable"].copy()
        self.assertTrue(rec_pay_account.reconcile)

        line_1 = self.create_line_for_reconciliation(
            -44.4, -28.8, foreign_currency, "2019-06-01", rec_pay_account
        )
        line_2 = self.create_line_for_reconciliation(
            44.41, 28.8, foreign_currency, "2019-06-01", rec_pay_account
        )
        amls = line_1 + line_2
        amls.reconcile()

        full_reconcile = amls.full_reconcile_id
        self.assertTrue(full_reconcile)

        partials = self._get_partials(amls)
        exchange_move = partials.exchange_move_id

        self.assertRecordValues(
            exchange_move.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "account_id": line_2.account_id.id,
                },
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_currency.id,
                    "account_id": self.exch_expense_account.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.sorted("amount"),
            [
                {
                    "amount": 0.01,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": exchange_move.line_ids.sorted("balance")[0].id,
                },
                {
                    "amount": 44.40,
                    "debit_amount_currency": 28.8,
                    "credit_amount_currency": 28.8,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_1.id,
                },
            ],
        )

    def test_reconcile_special_mexican_workflow_1(self):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.env["res.currency"].create(
            {
                "name": "Sushi",
                "symbol": "🍣",
                "rounding": 0.01,
                "rate_ids": [
                    Command.create({"name": "2019-09-24", "rate": 0.050800000000}),
                    Command.create({"name": "2019-06-28", "rate": 0.052235000000}),
                    Command.create({"name": "2019-06-24", "rate": 0.052686000000}),
                    Command.create({"name": "2019-06-20", "rate": 0.052353000000}),
                    Command.create({"name": "2019-06-12", "rate": 0.052072000000}),
                ],
            }
        )

        refund1 = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "invoice_date": "2019-06-12",
                "date": "2019-06-12",
                "partner_id": self.partner_a.id,
                "currency_id": self.company_data["currency"].id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 1385.92,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        refund1.action_post()
        refund1_rec_line = refund1.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        inv1 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2019-06-20",
                "date": "2019-06-20",
                "partner_id": self.partner_a.id,
                "currency_id": self.company_data["currency"].id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 839.40,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        inv1.action_post()
        inv1_rec_line = inv1.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        inv2 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2019-06-24",
                "date": "2019-06-24",
                "partner_id": self.partner_a.id,
                "currency_id": foreign_curr.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 1935.72,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        inv2.action_post()
        inv2_rec_line = inv2.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        pay1 = self.env["account.payment"].create(
            {
                "partner_type": "customer",
                "payment_type": "inbound",
                "date": "2019-06-28",
                "amount": 1907.17,
                "partner_id": self.partner_a.id,
                "currency_id": foreign_curr.id,
            }
        )
        pay1.action_post()
        pay1_liquidity_line = pay1.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type != "asset_receivable"
        )
        pay1_rec_line = pay1.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        pay1.move_id.action_draft()
        pay1.move_id.write(
            {
                "line_ids": [
                    Command.update(pay1_liquidity_line.id, {"debit": 36511.34}),
                    Command.update(pay1_rec_line.id, {"credit": 36511.34}),
                ]
            }
        )
        pay1.move_id.action_post()

        pay2 = self.env["account.payment"].create(
            {
                "partner_type": "customer",
                "payment_type": "inbound",
                "date": "2019-09-24",
                "amount": 0.09,
                "partner_id": self.partner_a.id,
                "currency_id": foreign_curr.id,
            }
        )
        pay2.action_post()
        pay2_rec_line = pay2.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        self.assert_invoice_outstanding_to_reconcile_widget(
            refund1,
            {
                inv1.id: 839.40,
                inv2.id: 36740.69,
            },
        )
        self.assertRecordValues(
            refund1_rec_line + inv1_rec_line,
            [
                {
                    "amount_residual": -1385.92,
                    "amount_residual_currency": -1385.92,
                    "reconciled": False,
                },
                {
                    "amount_residual": 839.40,
                    "amount_residual_currency": 839.40,
                    "reconciled": False,
                },
            ],
        )

        (refund1_rec_line + inv1_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv1_rec_line)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 839.4,
                    "debit_amount_currency": 839.4,
                    "credit_amount_currency": 839.4,
                    "debit_move_id": inv1_rec_line.id,
                    "credit_move_id": refund1_rec_line.id,
                    "exchange_move_id": None,
                }
            ],
        )
        self.assertRecordValues(
            refund1_rec_line + inv1_rec_line,
            [
                {
                    "amount_residual": -546.52,
                    "amount_residual_currency": -546.52,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )
        self.assert_invoice_outstanding_reconciled_widget(
            refund1,
            {
                inv1.id: 839.40,
            },
        )

        self.assert_invoice_outstanding_to_reconcile_widget(
            refund1,
            {
                inv2.id: 36740.69,
            },
        )
        self.assertRecordValues(
            refund1_rec_line + inv2_rec_line,
            [
                {
                    "amount_residual": -546.52,
                    "amount_residual_currency": -546.52,
                    "reconciled": False,
                },
                {
                    "amount_residual": 36740.69,
                    "amount_residual_currency": 1935.72,
                    "reconciled": False,
                },
            ],
        )

        partials = self._get_partials(refund1_rec_line + inv2_rec_line)
        (refund1_rec_line + inv2_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv2_rec_line) - partials

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 540.18,
                    "debit_amount_currency": 28.46,
                    "credit_amount_currency": 540.18,
                    "debit_move_id": inv2_rec_line.id,
                    "credit_move_id": refund1_rec_line.id,
                },
                {
                    "amount": 6.34,
                    "debit_amount_currency": 6.34,
                    "credit_amount_currency": 6.34,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": refund1_rec_line.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2019-06-30")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 6.34,
                    "credit": 0.0,
                    "amount_currency": 6.34,
                    "currency_id": comp_curr.id,
                    "account_id": refund1_rec_line.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 6.34,
                    "amount_currency": -6.34,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            refund1_rec_line + inv2_rec_line,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 36200.51,
                    "amount_residual_currency": 1907.26,
                    "reconciled": False,
                },
            ],
        )
        self.assert_invoice_outstanding_reconciled_widget(
            refund1,
            {
                inv1.id: 839.40,
                inv2.id: 540.18,
                partials.exchange_move_id.id: 6.34,
            },
        )
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {})

        self.assert_invoice_outstanding_reconciled_widget(
            inv2,
            {
                refund1.id: 28.46,
                partials.exchange_move_id.id: 6.34,
            },
        )
        self.assert_invoice_outstanding_to_reconcile_widget(
            inv2,
            {
                pay1.move_id.id: 1907.17,
                pay2.move_id.id: 0.09,
            },
        )
        self.assertRecordValues(
            inv2_rec_line + pay1_rec_line,
            [
                {
                    "amount_residual": 36200.51,
                    "amount_residual_currency": 1907.26,
                    "reconciled": False,
                },
                {
                    "amount_residual": -36511.34,
                    "amount_residual_currency": -1907.17,
                    "reconciled": False,
                },
            ],
        )

        partials = self._get_partials(inv2_rec_line + pay1_rec_line)
        (inv2_rec_line + pay1_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay1_rec_line) - partials

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 36198.80,
                    "debit_amount_currency": 1907.17,
                    "credit_amount_currency": 1907.17,
                    "debit_move_id": inv2_rec_line.id,
                    "credit_move_id": pay1_rec_line.id,
                },
                {
                    "amount": 312.54,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": pay1_rec_line.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2019-06-30")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 312.54,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": pay1_rec_line.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 312.54,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            inv2_rec_line + pay1_rec_line,
            [
                {
                    "amount_residual": 1.71,
                    "amount_residual_currency": 0.09,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(
            lambda x: x not in partials
        )

        self.assert_invoice_outstanding_reconciled_widget(
            inv2,
            {
                refund1.id: 28.46,
                pay1.move_id.id: 1907.17,
                partials.exchange_move_id.id: 312.54,
                payment_exchange_id[0].exchange_move_id.id: 6.34,
            },
        )

        self.assert_invoice_outstanding_to_reconcile_widget(
            inv2,
            {
                pay2.move_id.id: 0.09,
            },
        )
        self.assertRecordValues(
            inv2_rec_line + pay2_rec_line,
            [
                {
                    "amount_residual": 1.71,
                    "amount_residual_currency": 0.09,
                    "reconciled": False,
                },
                {
                    "amount_residual": -1.77,
                    "amount_residual_currency": -0.09,
                    "reconciled": False,
                },
            ],
        )

        partials = self._get_partials(inv2_rec_line + pay2_rec_line)
        (inv2_rec_line + pay2_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay2_rec_line) - partials

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 1.71,
                    "debit_amount_currency": 0.09,
                    "credit_amount_currency": 0.09,
                    "debit_move_id": inv2_rec_line.id,
                    "credit_move_id": pay2_rec_line.id,
                },
                {
                    "amount": 0.06,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": pay2_rec_line.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2019-09-30")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.06,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": inv2_rec_line.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.06,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            inv2_rec_line + pay2_rec_line,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(
            lambda x: x not in partials
        )

        self.assert_invoice_outstanding_reconciled_widget(
            inv2,
            {
                refund1.id: 28.46,
                pay1.move_id.id: 1907.17,
                pay2.move_id.id: 0.09,
                partials.exchange_move_id.id: 0.06,
                payment_exchange_id[0].exchange_move_id.id: 6.34,
                payment_exchange_id[1].exchange_move_id.id: 312.54,
            },
        )
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {})

    def test_reconcile_special_mexican_workflow_2(self):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.env["res.currency"].create(
            {
                "name": "Sushi",
                "symbol": "🍣",
                "rounding": 0.01,
                "rate_ids": [
                    Command.create({"name": "2019-09-24", "rate": 0.050800000000}),
                    Command.create({"name": "2019-06-28", "rate": 0.052235000000}),
                    Command.create({"name": "2019-06-24", "rate": 0.052686000000}),
                    Command.create({"name": "2019-06-20", "rate": 0.052353000000}),
                    Command.create({"name": "2019-06-12", "rate": 0.052072000000}),
                ],
            }
        )

        refund1 = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "invoice_date": "2019-06-12",
                "date": "2019-06-12",
                "partner_id": self.partner_a.id,
                "currency_id": self.company_data["currency"].id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 1385.92,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        refund1.action_post()
        refund1_rec_line = refund1.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        inv1 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2019-06-20",
                "date": "2019-06-20",
                "partner_id": self.partner_a.id,
                "currency_id": self.company_data["currency"].id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 839.40,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        inv1.action_post()
        inv1_rec_line = inv1.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        inv2 = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2019-06-24",
                "date": "2019-06-24",
                "partner_id": self.partner_a.id,
                "currency_id": foreign_curr.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 1935.72,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        inv2.action_post()
        inv2_rec_line = inv2.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        pay1 = self.env["account.payment"].create(
            {
                "partner_type": "customer",
                "payment_type": "inbound",
                "date": "2019-06-28",
                "amount": 1907.17,
                "partner_id": self.partner_a.id,
                "currency_id": foreign_curr.id,
            }
        )
        pay1.action_post()
        pay1_liquidity_line = pay1.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type != "asset_receivable"
        )
        pay1_rec_line = pay1.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        pay1.move_id.action_draft()
        pay1.move_id.write(
            {
                "line_ids": [
                    Command.update(pay1_liquidity_line.id, {"debit": 36511.34}),
                    Command.update(pay1_rec_line.id, {"credit": 36511.34}),
                ]
            }
        )
        pay1.action_post()

        pay2 = self.env["account.payment"].create(
            {
                "partner_type": "customer",
                "payment_type": "inbound",
                "date": "2019-09-24",
                "amount": 0.09,
                "partner_id": self.partner_a.id,
                "currency_id": foreign_curr.id,
            }
        )
        pay2.action_post()
        pay2_rec_line = pay2.move_id.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )

        self.assertRecordValues(
            refund1_rec_line
            + inv1_rec_line
            + inv2_rec_line
            + pay1_rec_line
            + pay2_rec_line,
            [
                {"amount_residual": -1385.92, "amount_residual_currency": -1385.92},
                {"amount_residual": 839.40, "amount_residual_currency": 839.40},
                {"amount_residual": 36740.69, "amount_residual_currency": 1935.72},
                {"amount_residual": -36511.34, "amount_residual_currency": -1907.17},
                {"amount_residual": -1.77, "amount_residual_currency": -0.09},
            ],
        )

        self.assert_invoice_outstanding_to_reconcile_widget(
            refund1,
            {
                inv1.id: 839.40,
                inv2.id: 36740.69,
            },
        )
        self.assertRecordValues(
            refund1_rec_line + inv1_rec_line,
            [
                {
                    "amount_residual": -1385.92,
                    "amount_residual_currency": -1385.92,
                    "reconciled": False,
                },
                {
                    "amount_residual": 839.40,
                    "amount_residual_currency": 839.40,
                    "reconciled": False,
                },
            ],
        )

        (refund1_rec_line + inv1_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv1_rec_line)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 839.4,
                    "debit_amount_currency": 839.4,
                    "credit_amount_currency": 839.4,
                    "debit_move_id": inv1_rec_line.id,
                    "credit_move_id": refund1_rec_line.id,
                    "exchange_move_id": None,
                }
            ],
        )
        self.assertRecordValues(
            refund1_rec_line + inv1_rec_line,
            [
                {
                    "amount_residual": -546.52,
                    "amount_residual_currency": -546.52,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )
        self.assert_invoice_outstanding_reconciled_widget(
            refund1,
            {
                inv1.id: 839.40,
            },
        )

        self.assert_invoice_outstanding_to_reconcile_widget(
            inv2,
            {
                refund1.id: 28.46,
                pay1.move_id.id: 1907.17,
                pay2.move_id.id: 0.09,
            },
        )
        self.assertRecordValues(
            refund1_rec_line + inv2_rec_line,
            [
                {
                    "amount_residual": -546.52,
                    "amount_residual_currency": -546.52,
                    "reconciled": False,
                },
                {
                    "amount_residual": 36740.69,
                    "amount_residual_currency": 1935.72,
                    "reconciled": False,
                },
            ],
        )

        (inv2_rec_line + pay1_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay1_rec_line)

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 36198.8,
                    "debit_amount_currency": 1907.17,
                    "credit_amount_currency": 1907.17,
                    "debit_move_id": inv2_rec_line.id,
                    "credit_move_id": pay1_rec_line.id,
                },
                {
                    "amount": 312.54,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": pay1_rec_line.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2019-06-30")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 312.54,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": inv2_rec_line.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 312.54,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            inv2_rec_line + pay1_rec_line,
            [
                {
                    "amount_residual": 541.89,
                    "amount_residual_currency": 28.55,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )
        self.assert_invoice_outstanding_reconciled_widget(
            inv2,
            {
                pay1.move_id.id: 1907.17,
                partials.exchange_move_id.id: 312.54,
            },
        )
        self.assert_invoice_outstanding_to_reconcile_widget(
            inv2,
            {
                refund1.id: 28.46,
                pay2.move_id.id: 0.09,
            },
        )

        self.assert_invoice_outstanding_to_reconcile_widget(
            refund1,
            {
                inv2.id: 541.89,
            },
        )
        self.assertRecordValues(
            refund1_rec_line + inv2_rec_line,
            [
                {
                    "amount_residual": -546.52,
                    "amount_residual_currency": -546.52,
                    "reconciled": False,
                },
                {
                    "amount_residual": 541.89,
                    "amount_residual_currency": 28.55,
                    "reconciled": False,
                },
            ],
        )

        partials = self._get_partials(refund1_rec_line + inv2_rec_line)
        (refund1_rec_line + inv2_rec_line).reconcile()
        partials = self._get_partials(refund1_rec_line + inv2_rec_line) - partials

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 540.18,
                    "debit_amount_currency": 28.46,
                    "credit_amount_currency": 540.18,
                    "debit_move_id": inv2_rec_line.id,
                    "credit_move_id": refund1_rec_line.id,
                },
                {
                    "amount": 6.34,
                    "debit_amount_currency": 6.34,
                    "credit_amount_currency": 6.34,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": refund1_rec_line.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2019-06-30")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 6.34,
                    "credit": 0.0,
                    "amount_currency": 6.34,
                    "currency_id": comp_curr.id,
                    "account_id": refund1_rec_line.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 6.34,
                    "amount_currency": -6.34,
                    "currency_id": comp_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            refund1_rec_line + inv2_rec_line,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 1.71,
                    "amount_residual_currency": 0.09,
                    "reconciled": False,
                },
            ],
        )
        self.assert_invoice_outstanding_reconciled_widget(
            refund1,
            {
                inv1.id: 839.40,
                inv2.id: 540.18,
                partials.exchange_move_id.id: 6.34,
            },
        )
        self.assert_invoice_outstanding_to_reconcile_widget(refund1, {})

        self.assert_invoice_outstanding_to_reconcile_widget(
            inv2,
            {
                pay2.move_id.id: 0.09,
            },
        )

        partials = self._get_partials(inv2_rec_line + pay2_rec_line)
        (inv2_rec_line + pay2_rec_line).reconcile()
        partials = self._get_partials(inv2_rec_line + pay2_rec_line) - partials

        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 1.71,
                    "debit_amount_currency": 0.09,
                    "credit_amount_currency": 0.09,
                    "debit_move_id": inv2_rec_line.id,
                    "credit_move_id": pay2_rec_line.id,
                },
                {
                    "amount": 0.06,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials.exchange_move_id.line_ids[0].id,
                    "credit_move_id": pay2_rec_line.id,
                },
            ],
        )
        self.assertRecordValues(
            partials.exchange_move_id, [{"date": fields.Date.from_string("2019-09-30")}]
        )
        self.assertRecordValues(
            partials.exchange_move_id.line_ids,
            [
                {
                    "debit": 0.06,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": inv2_rec_line.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.06,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            inv2_rec_line + pay2_rec_line,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )
        payment_exchange_id = inv2_rec_line.matched_credit_ids.filtered(
            lambda x: x not in partials
        )

        self.assert_invoice_outstanding_reconciled_widget(
            inv2,
            {
                refund1.id: 28.46,
                pay1.move_id.id: 1907.17,
                pay2.move_id.id: 0.09,
                partials.exchange_move_id.id: 0.06,
                payment_exchange_id[0].exchange_move_id.id: 312.54,
                payment_exchange_id[1].exchange_move_id.id: 6.34,
            },
        )
        self.assert_invoice_outstanding_to_reconcile_widget(inv2, {})

    def test_migration_to_new_reconciliation_same_foreign_currency(self):
        foreign_curr = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            -60.0, -120.0, foreign_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            80.0, 240.0, foreign_curr, "2016-01-01"
        )

        self.env["account.partial.reconcile"].create(
            {
                "amount": 60.0,
                "debit_amount_currency": 120.0,
                "credit_amount_currency": 120.0,
                "debit_move_id": line_2.id,
                "credit_move_id": line_1.id,
            }
        )
        self.assertRecordValues(
            line_1 + line_2,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 20.0,
                    "amount_residual_currency": 120.0,
                    "reconciled": False,
                },
            ],
        )

        line_3 = self.create_line_for_reconciliation(
            -15.0, -30.0, foreign_curr, "2017-01-01"
        )
        (line_2 + line_3).reconcile()
        self.assertRecordValues(
            line_2 + line_3,
            [
                {
                    "amount_residual": 10.0,
                    "amount_residual_currency": 90.0,
                    "reconciled": False,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

        line_4 = self.create_line_for_reconciliation(
            -30.0, -90.0, foreign_curr, "2016-01-01"
        )
        (line_2 + line_4).reconcile()
        self.assertRecordValues(
            line_2 + line_4,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_migration_to_new_reconciliation_multiple_currencies_fix_residual_with_writeoff(
        self,
    ):
        comp_curr = self.company_data["currency"]
        foreign_curr1 = self.other_currency

        line_1 = self.create_line_for_reconciliation(
            600.0, 1200.0, foreign_curr1, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -800.0, -2400.0, foreign_curr1, "2016-01-01"
        )
        line_3 = self.create_line_for_reconciliation(
            400.0, 400.0, comp_curr, "2016-01-01"
        )

        self.env["account.partial.reconcile"].create(
            [
                {
                    "amount": 600.0,
                    "debit_amount_currency": 1200.0,
                    "credit_amount_currency": 1200.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_2.id,
                },
                {
                    "amount": 200.0,
                    "debit_amount_currency": 200.0,
                    "credit_amount_currency": 600.0,
                    "debit_move_id": line_3.id,
                    "credit_move_id": line_2.id,
                },
            ]
        )
        self.assertRecordValues(
            line_1 + line_2 + line_3,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": -600.0,
                    "reconciled": False,
                },
                {
                    "amount_residual": 200.0,
                    "amount_residual_currency": 200.0,
                    "reconciled": False,
                },
            ],
        )

        line_4 = self.create_line_for_reconciliation(
            0.0, 600.0, foreign_curr1, "2016-01-01"
        )
        line_5 = self.create_line_for_reconciliation(
            -200.0, -200.0, comp_curr, "2016-01-01"
        )
        (line_2 + line_3 + line_4 + line_5).reconcile()

        self.assertRecordValues(
            line_1 + line_2 + line_3 + line_4 + line_5,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )

    def test_reconcile_rounding_issue(self):
        currency = self.setup_other_currency(
            "CHF", rates=[("2016-01-01", 1 / 1.5289), ("2017-01-01", 1 / 1.5289)]
        )

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "currency_id": currency.id,
                "date": "2017-01-01",
                "invoice_date": "2017-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 23.0,
                            "tax_ids": [
                                (6, 0, self.company_data["default_tax_sale"].ids)
                            ],
                        },
                    )
                ],
            }
        )
        invoice.action_post()

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create(
            {"amount": 100.0, "currency_id": self.company_data["currency"].id}
        )._create_payments()

        self.assertTrue(invoice.payment_state in ("in_payment", "paid"))

    def test_reconcile_plan(self):
        comp_curr = self.company_data["currency"]

        line_1 = self.create_line_for_reconciliation(
            600.0, 600.0, comp_curr, "2017-01-01"
        )
        line_2 = self.create_line_for_reconciliation(
            -100.0, -100.0, comp_curr, "2017-01-02"
        )
        line_3 = self.create_line_for_reconciliation(
            700.0, 700.0, comp_curr, "2017-01-03"
        )
        line_5 = self.create_line_for_reconciliation(
            -700.0, -700.0, comp_curr, "2017-01-04"
        )
        line_4 = self.create_line_for_reconciliation(
            -500.0, -500.0, comp_curr, "2017-01-05"
        )

        with closing(self.cr.savepoint()):
            self.env["account.move.line"]._reconcile_plan(
                [line_1, line_2, line_3, line_4, line_5]
            )
            self.assertFalse(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5)
            )

        with closing(self.cr.savepoint()):
            self.env["account.move.line"]._reconcile_plan(
                [line_1 + line_2 + line_3 + line_4 + line_5]
            )
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {
                        "amount": 100.0,
                        "debit_move_id": line_1.id,
                        "credit_move_id": line_2.id,
                    },
                    {
                        "amount": 500.0,
                        "debit_move_id": line_1.id,
                        "credit_move_id": line_5.id,
                    },
                    {
                        "amount": 200.0,
                        "debit_move_id": line_3.id,
                        "credit_move_id": line_5.id,
                    },
                    {
                        "amount": 500.0,
                        "debit_move_id": line_3.id,
                        "credit_move_id": line_4.id,
                    },
                ],
            )

        with closing(self.cr.savepoint()):
            self.env["account.move.line"]._reconcile_plan(
                [line_3 + line_5, line_1 + line_4, line_2]
            )
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {
                        "amount": 700.0,
                        "debit_move_id": line_3.id,
                        "credit_move_id": line_5.id,
                    },
                    {
                        "amount": 500.0,
                        "debit_move_id": line_1.id,
                        "credit_move_id": line_4.id,
                    },
                ],
            )

        with closing(self.cr.savepoint()):
            self.env["account.move.line"]._reconcile_plan(
                [[line_3 + line_5, line_1 + line_4, line_2]]
            )
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {
                        "amount": 700.0,
                        "debit_move_id": line_3.id,
                        "credit_move_id": line_5.id,
                    },
                    {
                        "amount": 500.0,
                        "debit_move_id": line_1.id,
                        "credit_move_id": line_4.id,
                    },
                    {
                        "amount": 100.0,
                        "debit_move_id": line_1.id,
                        "credit_move_id": line_2.id,
                    },
                ],
            )

        with closing(self.cr.savepoint()):
            self.env["account.move.line"]._reconcile_plan(
                [[[line_3 + line_5], [[line_1 + line_4], line_2]]]
            )
            self.assertRecordValues(
                self._get_partials(line_1 + line_2 + line_3 + line_4 + line_5),
                [
                    {
                        "amount": 700.0,
                        "debit_move_id": line_3.id,
                        "credit_move_id": line_5.id,
                    },
                    {
                        "amount": 500.0,
                        "debit_move_id": line_1.id,
                        "credit_move_id": line_4.id,
                    },
                    {
                        "amount": 100.0,
                        "debit_move_id": line_1.id,
                        "credit_move_id": line_2.id,
                    },
                ],
            )

    def _prepare_cash_basis_move(self):
        self.env.company.account_config_id.tax_exigibility = True
        self.cash_basis_tax_tiny_amount.amount = 0.01
        cash_basis_move = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "tax_ids": [
                                    (
                                        6,
                                        0,
                                        (
                                            self.cash_basis_tax_a_third_amount
                                            + self.cash_basis_tax_tiny_amount
                                        ).ids,
                                    )
                                ],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 33.33,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 0.01,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_tiny_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 44.45,
                                "credit": 0.0,
                                "account_id": self.extra_receivable_account_1.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 44.45,
                                "credit": 0.0,
                                "account_id": self.extra_receivable_account_2.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 44.45,
                                "credit": 0.0,
                                "account_id": self.extra_receivable_account_2.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 0.01,
                                "account_id": self.extra_payable_account_1.id,
                            },
                        ),
                    ],
                }
            )
        )
        cash_basis_move.line_ids.flush_model()
        return cash_basis_move

    def _prepare_cash_basis_payment(self):
        return self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 33.34,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 11.11,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 88.89,
                            "account_id": self.extra_receivable_account_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 0.01,
                            "account_id": self.extra_receivable_account_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.01,
                            "credit": 0.0,
                            "account_id": self.extra_payable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 133.34,
                            "credit": 0.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )

    def _prepare_cash_basis_move_and_payment(self):
        cash_basis_move = self._prepare_cash_basis_move()
        payment_move = self._prepare_cash_basis_payment()
        return cash_basis_move, payment_move

    def test_reconcile_cash_basis_workflow_single_currency(self):
        cash_basis_move, payment_move = self._prepare_cash_basis_move_and_payment()
        (cash_basis_move + payment_move).action_post()

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -33.34, -33.34),
                (self.tax_account_1, 0.0, 0.0),
                (self.tax_account_2, 0.0, 0.0),
                (self.cash_basis_base_account, 0.0, 0.0),
            ]
        )

        receivable_lines_1 = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_1.move_id)
        receivable_lines_1.reconcile()
        tax_cash_basis_moves = (
            self._get_caba_moves(receivable_lines_1.move_id) - tax_cash_basis_moves
        )

        self.assertFullReconcile(
            receivable_lines_1.full_reconcile_id, receivable_lines_1
        )
        self.assertEqual(len(tax_cash_basis_moves), 2)
        self.assertRecordValues(
            tax_cash_basis_moves[0].line_ids,
            [
                {
                    "debit": 8.33,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 8.33,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 2.78,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 2.78, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_2.id},
            ],
        )
        self.assertRecordValues(
            tax_cash_basis_moves[1].line_ids,
            [
                {
                    "debit": 25.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 25.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 8.33,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 8.33, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_2.id},
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -22.23, -22.23),
                (self.tax_account_1, -11.11, -11.11),
                (self.tax_account_2, 0.0, 0.0),
            ]
        )

        receivable_lines_2 = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_2
        )
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_2.move_id)
        receivable_lines_2.reconcile()
        tax_cash_basis_moves = (
            self._get_caba_moves(receivable_lines_2.move_id) - tax_cash_basis_moves
        )

        self.assertFullReconcile(
            receivable_lines_2.full_reconcile_id, receivable_lines_2
        )
        self.assertEqual(len(tax_cash_basis_moves), 3)
        self.assertRecordValues(
            tax_cash_basis_moves[0].line_ids,
            [
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_2.id},
            ],
        )
        self.assertRecordValues(
            tax_cash_basis_moves[1].line_ids,
            [
                {
                    "debit": 33.32,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 33.32,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 11.11,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 11.11, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_2.id},
            ],
        )
        self.assertRecordValues(
            tax_cash_basis_moves[2].line_ids,
            [
                {
                    "debit": 33.33,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 33.33,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 11.11,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 11.11, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_2.id},
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -0.01, -0.01),
                (self.tax_account_1, -33.33, -33.33),
                (self.tax_account_2, 0.0, 0.0),
            ]
        )

        payable_lines_1 = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_payable_account_1
        )
        tax_cash_basis_moves = self._get_caba_moves(payable_lines_1.move_id)
        payable_lines_1.reconcile()
        tax_cash_basis_moves = (
            self._get_caba_moves(payable_lines_1.move_id) - tax_cash_basis_moves
        )

        self.assertFullReconcile(payable_lines_1.full_reconcile_id, payable_lines_1)
        self.assertEqual(len(tax_cash_basis_moves), 1)
        self.assertRecordValues(
            tax_cash_basis_moves.line_ids,
            [
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.01, "account_id": self.tax_account_2.id},
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, 0.0, 0.0),
                (self.tax_account_1, -33.33, -33.33),
                (self.tax_account_2, -0.01, -0.01),
            ]
        )

    def test_reconcile_draft_cash_basis_surprise_use_case(self):
        self.env.company.account_config_id.tax_exigibility = True
        caba_tax = self.env["account.tax"].create(
            {
                "name": "cash basis 20%",
                "type_tax_use": "purchase",
                "amount": 20,
                "tax_exigibility": "on_payment",
                "analytic": True,
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
            }
        )
        tax = self.env["account.tax"].create(
            {
                "name": "tax 20%",
                "type_tax_use": "purchase",
                "amount": 20,
                "tax_exigibility": "on_invoice",
                "analytic": True,
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
            }
        )
        inv = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2019-06-20",
                "date": "2019-06-20",
                "partner_id": self.partner_a.id,
                "currency_id": self.company_data["currency"].id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 100,
                            "tax_ids": [Command.set(tax.ids)],
                        }
                    )
                ],
            }
        )
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=inv.ids)
            .create(
                {
                    "payment_date": inv.date,
                }
            )
            ._create_payments()
        )

        inv_rec_line = inv.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        self.assertTrue(inv_rec_line.full_reconcile_id)
        tax_cash_basis_moves = self._get_caba_moves(inv)
        self.assertEqual(len(tax_cash_basis_moves), 0)

        inv.invoice_line_ids[0].tax_ids = [Command.set(caba_tax.ids)]
        inv.action_post()

        self.assertFalse(inv_rec_line.full_reconcile_id)
        receivable_lines = (inv + payment.move_id).line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        receivable_lines.reconcile()
        self.assertTrue(inv_rec_line.full_reconcile_id)
        tax_cash_basis_moves = self._get_caba_moves(inv)
        self.assertEqual(len(tax_cash_basis_moves), 1)
        self.assertEqual(tax_cash_basis_moves.state, "posted")

    def test_reconcile_cash_basis_mixed_posted_draft_transfer_account(self):
        self.env.company.account_config_id.tax_exigibility = True
        tax = self.cash_basis_tax_a_third_amount
        tax_rep_line = tax.invoice_repartition_line_ids.filtered(
            lambda line: line.repartition_type == "tax"
        )

        def _origin_move(base, tax_amount):
            return (
                self.env["account.move"]
                .with_context(skip_invoice_sync=True)
                .create(
                    {
                        "move_type": "entry",
                        "date": "2016-01-01",
                        "line_ids": [
                            Command.create(
                                {
                                    "debit": 0.0,
                                    "credit": base,
                                    "account_id": self.company_data[
                                        "default_account_revenue"
                                    ].id,
                                    "tax_ids": [Command.set(tax.ids)],
                                }
                            ),
                            Command.create(
                                {
                                    "debit": 0.0,
                                    "credit": tax_amount,
                                    "account_id": self.cash_basis_transfer_account.id,
                                    "tax_repartition_line_id": tax_rep_line.id,
                                }
                            ),
                            Command.create(
                                {
                                    "debit": base + tax_amount,
                                    "credit": 0.0,
                                    "account_id": self.extra_receivable_account_1.id,
                                }
                            ),
                        ],
                    }
                )
            )

        origin_draft = _origin_move(100.0, 33.33)
        origin_posted = _origin_move(200.0, 66.66)
        origin_posted.action_post()

        payment = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 399.99,
                                "account_id": self.extra_receivable_account_1.id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 399.99,
                                "credit": 0.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                    ],
                }
            )
        )
        payment.action_post()

        receivable_lines = (origin_posted + origin_draft + payment).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()

        for origin in origin_posted + origin_draft:
            origin_tax_line = origin.line_ids.filtered(
                lambda line: line.account_id == self.cash_basis_transfer_account
            )
            partials = (
                origin_tax_line.matched_debit_ids | origin_tax_line.matched_credit_ids
            )
            counterparts = (
                partials.debit_move_id | partials.credit_move_id
            ) - origin_tax_line
            caba_counterparts = counterparts.filtered(
                lambda line: line.move_id.tax_cash_basis_origin_move_id
            )
            self.assertTrue(
                caba_counterparts,
                "the origin transfer tax line should reconcile with a cash basis move",
            )
            for counterpart in caba_counterparts:
                self.assertEqual(
                    counterpart.move_id.tax_cash_basis_origin_move_id,
                    origin,
                    "cash basis transfer line reconciled across origins "
                    "(move_index desynchronized by post/draft reordering)",
                )

    def test_reconcile_draft_cash_basis_use_case(self):
        cash_basis_move = self._prepare_cash_basis_move()
        payment_move_1 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 33.34,
                            "account_id": self.extra_receivable_account_1.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 33.34,
                            "credit": 0.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )
        payment_move_1.action_post()
        payment_move_2 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 11.11,
                            "account_id": self.extra_receivable_account_1.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 11.11,
                            "credit": 0.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -33.34, -33.34),
                (self.tax_account_1, 0.0, 0.0),
                (self.tax_account_2, 0.0, 0.0),
                (self.cash_basis_base_account, 0.0, 0.0),
            ]
        )

        receivable_lines_1 = (
            cash_basis_move + payment_move_1 + payment_move_2
        ).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines_1.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_1.move_id)

        self.assertFullReconcile(
            receivable_lines_1.full_reconcile_id, receivable_lines_1
        )
        self.assertEqual(len(tax_cash_basis_moves), 2)
        self.assertEqual(
            len(tax_cash_basis_moves.filtered(lambda m: m.state == "posted")), 0
        )
        self.assertRecordValues(
            tax_cash_basis_moves[0].line_ids,
            [
                {
                    "debit": 8.33,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 8.33,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 2.78,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 2.78, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_2.id},
            ],
        )
        self.assertRecordValues(
            tax_cash_basis_moves[1].line_ids,
            [
                {
                    "debit": 25.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 25.0,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 8.33,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 8.33, "account_id": self.tax_account_1.id},
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {"debit": 0.0, "credit": 0.0, "account_id": self.tax_account_2.id},
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -22.23, -22.23),
                (self.tax_account_1, -11.11, -11.11),
                (self.tax_account_2, 0.0, 0.0),
            ]
        )

        cash_basis_move.action_post()
        self.assertEqual(
            len(tax_cash_basis_moves.filtered(lambda m: m.state == "posted")), 1
        )
        payment_move_2.action_post()
        self.assertEqual(
            len(tax_cash_basis_moves.filtered(lambda m: m.state == "posted")), 2
        )

    def test_reconcile_draft_exchange_diff_use_case(self):
        comp_curr = self.company_data["currency"]
        foreign_curr = self.other_currency
        invoice = self.create_line_for_reconciliation(
            40.0, 40.0, comp_curr, "2016-01-01"
        )
        payment_1 = self.create_line_for_reconciliation(
            -30.0, -60.0, foreign_curr, "2017-01-01"
        )
        payment_2 = self.create_line_for_reconciliation(
            -30.0, -60.0, foreign_curr, "2017-01-01"
        )
        (invoice.move_id + payment_2.move_id).action_draft()
        amls = invoice + payment_1 + payment_2
        amls.reconcile()
        partials = self._get_partials(amls)
        self.assertEqual(len(partials), 4)
        self.assertRecordValues(
            partials,
            [
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 60.0,
                    "debit_move_id": invoice.id,
                    "credit_move_id": payment_1.id,
                },
                {
                    "amount": 20.0,
                    "debit_amount_currency": 20.0,
                    "credit_amount_currency": 60.0,
                    "debit_move_id": invoice.id,
                    "credit_move_id": payment_2.id,
                },
                {
                    "amount": 10.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials[0].exchange_move_id.line_ids[0].id,
                    "credit_move_id": payment_1.id,
                },
                {
                    "amount": 10.0,
                    "debit_amount_currency": 0.0,
                    "credit_amount_currency": 0.0,
                    "debit_move_id": partials[1].exchange_move_id.line_ids[0].id,
                    "credit_move_id": payment_2.id,
                },
            ],
        )
        self.assertRecordValues(
            partials[0].exchange_move_id,
            [{"date": fields.Date.from_string("2017-01-31"), "state": "draft"}],
        )
        self.assertRecordValues(
            partials[0].exchange_move_id.line_ids,
            [
                {
                    "debit": 10.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": payment_1.account_id.id,
                },
                {
                    "debit": 0.0,
                    "credit": 10.0,
                    "amount_currency": 0.0,
                    "currency_id": foreign_curr.id,
                    "account_id": self.exch_income_account.id,
                },
            ],
        )
        self.assertRecordValues(
            amls,
            [
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
                {
                    "amount_residual": 0.0,
                    "amount_residual_currency": 0.0,
                    "reconciled": True,
                },
            ],
        )
        exchange_moves = partials.exchange_move_id
        self.assertEqual(exchange_moves.mapped("state"), ["draft", "draft"])
        invoice.move_id.action_post()
        self.assertEqual(exchange_moves.mapped("state"), ["posted", "draft"])
        payment_2.move_id.action_post()
        self.assertEqual(exchange_moves.mapped("state"), ["posted", "posted"])

    def test_reconcile_cash_basis_workflow_multi_currency(self):
        self.env.company.account_config_id.tax_exigibility = True
        currency_id = self.other_currency.id
        taxes = self.cash_basis_tax_a_third_amount + self.cash_basis_tax_tiny_amount

        cash_basis_move = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 33.34,
                                "amount_currency": -100.0,
                                "currency_id": currency_id,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "tax_ids": [(6, 0, taxes.ids)],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 11.10,
                                "amount_currency": -33.33,
                                "currency_id": currency_id,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 0.01,
                                "amount_currency": -0.01,
                                "currency_id": currency_id,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_tiny_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 14.82,
                                "credit": 0.0,
                                "amount_currency": 44.45,
                                "currency_id": currency_id,
                                "account_id": self.extra_receivable_account_1.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 14.82,
                                "credit": 0.0,
                                "amount_currency": 44.45,
                                "currency_id": currency_id,
                                "account_id": self.extra_receivable_account_2.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 14.82,
                                "credit": 0.0,
                                "amount_currency": 44.45,
                                "currency_id": currency_id,
                                "account_id": self.extra_receivable_account_2.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 0.01,
                                "amount_currency": -0.01,
                                "currency_id": currency_id,
                                "account_id": self.extra_payable_account_1.id,
                            },
                        ),
                    ],
                }
            )
        )

        payment_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 16.67,
                            "amount_currency": -33.34,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 5.6,
                            "amount_currency": -11.11,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 44.45,
                            "amount_currency": -88.89,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 0.01,
                            "amount_currency": -0.01,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_2.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.01,
                            "credit": 0.0,
                            "amount_currency": 0.01,
                            "currency_id": currency_id,
                            "account_id": self.extra_payable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 66.72,
                            "credit": 0.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )

        (cash_basis_move + payment_move).action_post()

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -11.11, -33.34),
                (self.tax_account_1, 0.0, 0.0),
                (self.tax_account_2, 0.0, 0.0),
            ]
        )

        receivable_lines_1 = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines_1.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_1.move_id)

        self.assertFullReconcileAccount(
            receivable_lines_1.full_reconcile_id, self.extra_receivable_account_1
        )
        self.assertEqual(len(tax_cash_basis_moves), 2)
        self.assertRecordValues(
            tax_cash_basis_moves[0].line_ids,
            [
                {
                    "debit": 4.2,
                    "credit": 0.0,
                    "amount_currency": 8.331,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 4.2,
                    "amount_currency": -8.331,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 1.4,
                    "credit": 0.0,
                    "amount_currency": 2.777,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 1.4,
                    "amount_currency": -2.777,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.001,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -0.001,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_2.id,
                },
            ],
        )
        self.assertRecordValues(
            tax_cash_basis_moves[1].line_ids,
            [
                {
                    "debit": 12.5,
                    "credit": 0.0,
                    "amount_currency": 25.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 12.5,
                    "amount_currency": -25.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 4.17,
                    "credit": 0.0,
                    "amount_currency": 8.333,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 4.17,
                    "amount_currency": -8.333,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.003,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -0.003,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_2.id,
                },
            ],
        )

        caba_transition_lines_1 = tax_cash_basis_moves.line_ids.filtered(
            lambda x: x.account_id == self.cash_basis_transfer_account
        )
        caba_transition_exchange_moves_1 = (
            caba_transition_lines_1.matched_credit_ids.exchange_move_id
        )
        self.assertEqual(len(caba_transition_exchange_moves_1), 2)
        self.assertRecordValues(
            caba_transition_exchange_moves_1[0].line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 0.48,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.48,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.env.company.account_config_id.expense_currency_exchange_account_id.id,
                },
            ],
        )
        self.assertRecordValues(
            caba_transition_exchange_moves_1[1].line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 1.39,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 1.39,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.env.company.account_config_id.expense_currency_exchange_account_id.id,
                },
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -7.41, -22.226),
                (self.tax_account_1, -5.57, -11.11),
                (self.tax_account_2, 0.0, -0.004),
            ]
        )

        receivable_lines_2 = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_2
        )
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines_2.move_id)
        receivable_lines_2.reconcile()
        tax_cash_basis_moves = (
            self._get_caba_moves(receivable_lines_2.move_id) - tax_cash_basis_moves
        )

        self.assertFullReconcileAccount(
            receivable_lines_2.full_reconcile_id, self.extra_receivable_account_2
        )
        self.assertEqual(len(tax_cash_basis_moves), 3)
        self.assertRecordValues(
            tax_cash_basis_moves[0].line_ids,
            [
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "amount_currency": 0.007,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "amount_currency": -0.007,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.002,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -0.002,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_2.id,
                },
            ],
        )
        self.assertRecordValues(
            tax_cash_basis_moves[1].line_ids,
            [
                {
                    "debit": 16.66,
                    "credit": 0.0,
                    "amount_currency": 33.323,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 16.66,
                    "amount_currency": -33.323,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 5.55,
                    "credit": 0.0,
                    "amount_currency": 11.107,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 5.55,
                    "amount_currency": -11.107,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.003,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -0.003,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_2.id,
                },
            ],
        )
        self.assertRecordValues(
            tax_cash_basis_moves[2].line_ids,
            [
                {
                    "debit": 16.67,
                    "credit": 0.0,
                    "amount_currency": 33.331,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 16.67,
                    "amount_currency": -33.331,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 5.56,
                    "credit": 0.0,
                    "amount_currency": 11.109,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 5.56,
                    "amount_currency": -11.109,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.003,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -0.003,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_2.id,
                },
            ],
        )

        caba_transition_lines_2 = tax_cash_basis_moves.line_ids.filtered(
            lambda x: x.account_id == self.cash_basis_transfer_account
        )
        caba_transition_exchange_moves_2 = (
            caba_transition_lines_2.matched_credit_ids.exchange_move_id
        ).sorted("id")
        self.assertEqual(len(caba_transition_exchange_moves_2), 3)
        self.assertRecordValues(
            caba_transition_exchange_moves_2[0].line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 1.86,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 1.86,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.env.company.account_config_id.expense_currency_exchange_account_id.id,
                },
            ],
        )
        self.assertRecordValues(
            caba_transition_exchange_moves_2[1].line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 1.85,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 1.85,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.env.company.account_config_id.expense_currency_exchange_account_id.id,
                },
            ],
        )

        self.assertRecordValues(
            caba_transition_exchange_moves_2[2].line_ids,
            [
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.env.company.account_config_id.income_currency_exchange_account_id.id,
                },
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, 0.0, -0.002),
                (self.tax_account_1, -16.68, -33.328),
                (self.tax_account_2, 0.0, -0.01),
            ]
        )

        payable_lines_1 = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_payable_account_1
        )
        tax_cash_basis_moves = self._get_caba_moves(payable_lines_1.move_id)
        payable_lines_1.reconcile()
        tax_cash_basis_moves = (
            self._get_caba_moves(payable_lines_1.move_id) - tax_cash_basis_moves
        )

        self.assertFullReconcile(payable_lines_1.full_reconcile_id, payable_lines_1)
        self.assertEqual(len(tax_cash_basis_moves), 1)
        self.assertRecordValues(
            tax_cash_basis_moves.line_ids,
            [
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "amount_currency": 0.007,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "amount_currency": -0.007,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.002,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -0.002,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_2.id,
                },
            ],
        )

        caba_transition_lines_3 = tax_cash_basis_moves.line_ids.filtered(
            lambda x: x.account_id == self.cash_basis_transfer_account
        )
        self.assertFalse(caba_transition_lines_3.matched_credit_ids.exchange_move_id)

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, 0.0, 0.0),
                (self.tax_account_1, -16.68, -33.33),
                (self.tax_account_2, 0.0, -0.01),
            ]
        )

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_1(
        self,
    ):
        self.env.company.account_config_id.tax_exigibility = True
        currency_id = self.other_currency.id

        cash_basis_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2016-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 100.0,
                            "amount_currency": -300.0,
                            "currency_id": currency_id,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 33.33,
                            "amount_currency": -100.0,
                            "currency_id": currency_id,
                            "account_id": self.cash_basis_transfer_account.id,
                            "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                lambda line: line.repartition_type == "tax"
                            ).id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 133.33,
                            "credit": 0.0,
                            "amount_currency": 400.0,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                ],
            }
        )

        payment_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 201.0,
                            "amount_currency": -402.0,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 201.0,
                            "credit": 0.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )

        end_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 1.0,
                            "credit": 0.0,
                            "amount_currency": 2.0,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 1.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )

        (cash_basis_move + payment_move + end_move).action_post()

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, -33.33, -100.0),
                (self.tax_account_1, 0.0, 0.0),
            ]
        )

        receivable_lines = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertEqual(len(tax_cash_basis_moves), 1)
        self.assertRecordValues(
            tax_cash_basis_moves.line_ids,
            [
                {
                    "debit": 150.0,
                    "credit": 0.0,
                    "amount_currency": 300.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 150.0,
                    "amount_currency": -300.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 50.0,
                    "credit": 0.0,
                    "amount_currency": 100.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 50.0,
                    "amount_currency": -100.0,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
            ],
        )

        receivable_lines2 = (payment_move + end_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines2.reconcile()

        self.assertTrue(receivable_lines2.full_reconcile_id)

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, 0.0, 0.0),
                (self.tax_account_1, -50.0, -100.0),
            ]
        )

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_2(
        self,
    ):
        self.env.company.account_config_id.tax_exigibility = True
        currency_id = self.setup_other_currency(
            "CHF", rates=[("2016-01-01", 0.5), ("2017-01-01", 0.66666666666666)]
        ).id

        caba_inv = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 200.0,
                                "amount_currency": -100.0,
                                "currency_id": currency_id,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "tax_ids": [
                                    (6, 0, self.cash_basis_tax_a_third_amount.ids)
                                ],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 20.0,
                                "amount_currency": -10.0,
                                "currency_id": currency_id,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 220.0,
                                "credit": 0.0,
                                "amount_currency": 110.0,
                                "currency_id": currency_id,
                                "account_id": self.extra_receivable_account_1.id,
                            },
                        ),
                    ],
                }
            )
        )
        caba_inv.action_post()

        pmt_wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=caba_inv.ids)
            .create(
                {
                    "payment_date": "2017-01-01",
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "payment_channel_id": self.inbound_payment_channel.id,
                }
            )
        )
        pmt_wizard._create_payments()
        partial_rec = caba_inv.mapped("line_ids.matched_credit_ids")
        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_rec_id", "in", partial_rec.ids)]
        )

        self.assertRecordValues(
            caba_move.line_ids,
            [
                {
                    "account_id": self.cash_basis_base_account.id,
                    "debit": 150.0,
                    "credit": 0.0,
                    "amount_currency": 100.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
                {
                    "account_id": self.cash_basis_base_account.id,
                    "debit": 0.0,
                    "credit": 150.0,
                    "amount_currency": -100.0,
                    "tax_ids": self.cash_basis_tax_a_third_amount.ids,
                    "tax_line_id": False,
                },
                {
                    "account_id": self.cash_basis_transfer_account.id,
                    "debit": 15.0,
                    "credit": 0.0,
                    "amount_currency": 10.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
                {
                    "account_id": self.tax_account_1.id,
                    "debit": 0.0,
                    "credit": 15.0,
                    "amount_currency": -10.0,
                    "tax_ids": [],
                    "tax_line_id": self.cash_basis_tax_a_third_amount.id,
                },
            ],
        )

        receivable_line = caba_inv.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        self.assertTrue(
            receivable_line.full_reconcile_id, "Invoice should be fully paid"
        )

        self.assertRecordValues(
            partial_rec.exchange_move_id.line_ids,
            [
                {
                    "account_id": receivable_line.account_id.id,
                    "debit": 0.0,
                    "credit": 55.0,
                    "amount_currency": 0.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
                {
                    "account_id": caba_move.company_id.account_config_id.expense_currency_exchange_account_id.id,
                    "debit": 55.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, 0.0, 0.0),
                (self.tax_account_1, -15.0, -10.0),
            ]
        )

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_3(
        self,
    ):
        self.env.company.account_config_id.tax_exigibility = True
        currency_id = self.setup_other_currency(
            "CHF", rates=[("2016-01-01", 0.5), ("2017-01-01", 0.66666666666666)]
        ).id

        caba_inv = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 200.0,
                                "amount_currency": -100.0,
                                "currency_id": currency_id,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "tax_ids": [
                                    (6, 0, self.cash_basis_tax_a_third_amount.ids)
                                ],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 20.0,
                                "amount_currency": -10.0,
                                "currency_id": currency_id,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 220.0,
                                "credit": 0.0,
                                "amount_currency": 110.0,
                                "currency_id": currency_id,
                                "account_id": self.extra_receivable_account_1.id,
                            },
                        ),
                    ],
                }
            )
        )
        caba_inv.action_post()

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=caba_inv.ids
        ).create(
            {
                "payment_date": "2017-01-01",
                "currency_id": currency_id,
                "amount": 110.0,
            }
        )._create_payments()

        receivable_line = caba_inv.line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        partial_rec = caba_inv.line_ids.matched_credit_ids
        self.assertTrue(
            receivable_line.full_reconcile_id, "Invoice should be fully paid"
        )

        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_rec_id", "in", caba_inv.line_ids.matched_credit_ids.ids)]
        )
        self.assertRecordValues(
            caba_move.line_ids,
            [
                {
                    "account_id": self.cash_basis_base_account.id,
                    "debit": 150.0,
                    "credit": 0.0,
                    "amount_currency": 100.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
                {
                    "account_id": self.cash_basis_base_account.id,
                    "debit": 0.0,
                    "credit": 150.0,
                    "amount_currency": -100.0,
                    "tax_ids": self.cash_basis_tax_a_third_amount.ids,
                    "tax_line_id": False,
                },
                {
                    "account_id": self.cash_basis_transfer_account.id,
                    "debit": 15.0,
                    "credit": 0.0,
                    "amount_currency": 10.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
                {
                    "account_id": self.tax_account_1.id,
                    "debit": 0.0,
                    "credit": 15.0,
                    "amount_currency": -10.0,
                    "tax_ids": [],
                    "tax_line_id": self.cash_basis_tax_a_third_amount.id,
                },
            ],
        )

        self.assertRecordValues(
            partial_rec.exchange_move_id.line_ids,
            [
                {
                    "account_id": self.extra_receivable_account_1.id,
                    "debit": 0.0,
                    "credit": 55.0,
                    "amount_currency": 0.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
                {
                    "account_id": caba_move.company_id.account_config_id.expense_currency_exchange_account_id.id,
                    "debit": 55.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "tax_ids": [],
                    "tax_line_id": False,
                },
            ],
        )

        self.assertAmountsGroupByAccount(
            [
                (self.cash_basis_transfer_account, 0.0, 0.0),
                (self.tax_account_1, -15.0, -10.0),
            ]
        )

    def test_reconcile_cash_basis_exchange_difference_transfer_account_check_entries_4(
        self,
    ):
        self.env.company.account_config_id.tax_exigibility = True
        currency_id = self.other_currency.id
        cash_basis_transition_account = self.env["account.account"].create(
            {
                "code": "209.01.01",
                "name": "Cash Basis Transition Account",
                "account_type": "liability_current",
                "reconcile": True,
            }
        )
        self.cash_basis_tax_a_third_amount.write(
            {
                "cash_basis_transition_account_id": cash_basis_transition_account.id,
            }
        )

        cash_basis_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2016-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 100.0,
                            "amount_currency": -300.0,
                            "currency_id": currency_id,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 33.33,
                            "amount_currency": -100.0,
                            "currency_id": currency_id,
                            "account_id": cash_basis_transition_account.id,
                            "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                lambda line: line.repartition_type == "tax"
                            ).id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 133.33,
                            "credit": 0.0,
                            "amount_currency": 400.0,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                ],
            }
        )

        payment_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 200.0,
                            "amount_currency": -400.0,
                            "currency_id": currency_id,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 200.0,
                            "credit": 0.0,
                            "amount_currency": 400.0,
                            "currency_id": currency_id,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )

        (cash_basis_move + payment_move).action_post()

        self.assertAmountsGroupByAccount(
            [
                (cash_basis_transition_account, -33.33, -100.0),
                (self.tax_account_1, 0.0, 0.0),
            ]
        )

        receivable_lines = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertEqual(len(tax_cash_basis_moves), 1)

        self.assertRecordValues(
            tax_cash_basis_moves.line_ids,
            [
                {
                    "debit": 150.0,
                    "credit": 0.0,
                    "amount_currency": 300.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 150.0,
                    "amount_currency": -300.0,
                    "currency_id": currency_id,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 50.0,
                    "credit": 0.0,
                    "amount_currency": 100.0,
                    "currency_id": currency_id,
                    "account_id": cash_basis_transition_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 50.0,
                    "amount_currency": -100.0,
                    "currency_id": currency_id,
                    "account_id": self.tax_account_1.id,
                },
            ],
        )

        partial_rec = cash_basis_move.line_ids.matched_credit_ids
        self.assertRecordValues(
            partial_rec.exchange_move_id.line_ids,
            [
                {
                    "debit": 66.67,
                    "credit": 0.0,
                    "currency_id": currency_id,
                    "account_id": self.extra_receivable_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 66.67,
                    "currency_id": currency_id,
                    "account_id": self.company_data[
                        "company"
                    ].account_config_id.income_currency_exchange_account_id.id,
                },
            ],
        )

    def test_reconcile_cash_basis_refund_multicurrency(self):
        self.env.company.account_config_id.tax_exigibility = True
        currency = self.setup_other_currency(
            "CHF", rates=[("2016-01-01", 0.5), ("2017-01-01", 0.33333333333333333)]
        )

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "currency_id": currency.id,
                "invoice_date": "2016-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "dudu",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        },
                    )
                ],
            }
        )

        refund = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner_a.id,
                "currency_id": currency.id,
                "invoice_date": "2017-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "dudu",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "price_unit": 100.0,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        },
                    )
                ],
            }
        )

        invoice.action_post()
        refund.action_post()

        (refund + invoice).line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        ).reconcile()

        self.assertRecordValues(
            self.env["account.move"]
            .search([("tax_cash_basis_origin_move_id", "=", invoice.id)])
            .line_ids,
            [
                {
                    "debit": 200.01,
                    "credit": 0,
                    "amount_currency": 100,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": [],
                },
                {
                    "debit": 0,
                    "credit": 200.01,
                    "amount_currency": -100,
                    "currency_id": currency.id,
                    "tax_ids": self.cash_basis_tax_a_third_amount.ids,
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": self.tax_tags[0].ids,
                },
                {
                    "debit": 66.66,
                    "credit": 0,
                    "amount_currency": 33.33,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": [],
                },
                {
                    "debit": 0,
                    "credit": 66.66,
                    "amount_currency": -33.33,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                        lambda x: x.repartition_type == "tax"
                    ).id,
                    "tax_tag_ids": self.tax_tags[1].ids,
                },
            ],
        )

        self.assertRecordValues(
            self.env["account.move"]
            .search([("tax_cash_basis_origin_move_id", "=", refund.id)])
            .line_ids,
            [
                {
                    "debit": 0,
                    "credit": 300.01,
                    "amount_currency": -100,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": [],
                },
                {
                    "debit": 300.01,
                    "credit": 0,
                    "amount_currency": 100,
                    "currency_id": currency.id,
                    "tax_ids": self.cash_basis_tax_a_third_amount.ids,
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": self.tax_tags[2].ids,
                },
                {
                    "debit": 0,
                    "credit": 99.99,
                    "amount_currency": -33.33,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": [],
                },
                {
                    "debit": 99.99,
                    "credit": 0,
                    "amount_currency": 33.33,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.refund_repartition_line_ids.filtered(
                        lambda x: x.repartition_type == "tax"
                    ).id,
                    "tax_tag_ids": self.tax_tags[3].ids,
                },
            ],
        )

        self.assertRecordValues(
            invoice.line_ids.filtered(
                lambda x: x.account_id.account_type == "asset_receivable"
            ).matched_credit_ids.exchange_move_id.line_ids,
            [
                {
                    "debit": 133.33,
                    "credit": 0,
                    "amount_currency": 0,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": [],
                },
                {
                    "debit": 0,
                    "credit": 133.33,
                    "amount_currency": 0,
                    "currency_id": currency.id,
                    "tax_ids": [],
                    "tax_repartition_line_id": None,
                    "tax_tag_ids": [],
                },
            ],
        )

    def test_reconcile_cash_basis_revert(self):
        self.env.company.account_config_id.tax_exigibility = True
        self.cash_basis_transfer_account.reconcile = True
        self.tax_account_1.reconcile = True
        self.cash_basis_tax_a_third_amount.cash_basis_transition_account_id = (
            self.tax_account_1
        )

        invoice_move = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "tax_ids": [
                                    (6, 0, self.cash_basis_tax_a_third_amount.ids)
                                ],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 33.33,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 133.33,
                                "credit": 0.0,
                                "account_id": self.extra_receivable_account_1.id,
                            },
                        ),
                    ],
                }
            )
        )

        payment_move = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 133.33,
                                "account_id": self.extra_receivable_account_1.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 133.33,
                                "credit": 0.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                    ],
                }
            )
        )

        (invoice_move + payment_move).action_post()

        receivable_lines = (invoice_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)
        self.assertEqual(len(tax_cash_basis_moves), 1)

        tax_cash_basis_move = tax_cash_basis_moves

        taxes_lines = (
            invoice_move.line_ids + tax_cash_basis_move.line_ids.filtered("debit")
        ).filtered(lambda line: line.account_id == self.cash_basis_transfer_account)
        taxes_full_reconcile = taxes_lines.matched_debit_ids.full_reconcile_id

        self.assertTrue(taxes_full_reconcile)
        self.assertFullReconcile(taxes_full_reconcile, taxes_lines)

        tax_cash_basis_move_reverse = tax_cash_basis_move._reverse_moves(cancel=True)

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)

        reversed_taxes_lines = (
            tax_cash_basis_move + tax_cash_basis_move_reverse
        ).line_ids.filtered(
            lambda line: line.account_id == self.cash_basis_transfer_account
        )

        reversed_taxes_full_reconcile = (
            reversed_taxes_lines.matched_debit_ids.full_reconcile_id
        )

        self.assertTrue(reversed_taxes_full_reconcile)
        self.assertFullReconcile(reversed_taxes_full_reconcile, reversed_taxes_lines)

    def test_reconcile_cash_basis_tax_grid_refund(self):
        self.env.company.account_config_id.tax_exigibility = True
        invoice_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2016-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 100.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 33.33,
                            "account_id": self.cash_basis_transfer_account.id,
                            "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                lambda line: line.repartition_type == "tax"
                            ).id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 133.33,
                            "credit": 0.0,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                ],
            }
        )

        refund_move = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "partner_id": self.partner_a.id,
                "invoice_date": "2016-01-01",
                "date": "2016-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "price_unit": 100.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        }
                    ),
                ],
            }
        )
        refund_move.line_ids.filtered(
            lambda l: l.display_type == "payment_term"
        ).account_id = self.extra_receivable_account_1

        (invoice_move + refund_move).action_post()

        receivable_lines = (invoice_move + refund_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)
        self.assertEqual(len(tax_cash_basis_moves), 2)

        tax_cash_basis_moves = tax_cash_basis_moves.sorted(
            lambda move: move.tax_cash_basis_origin_move_id.id
        )

        cb_lines = tax_cash_basis_moves[0].line_ids.sorted(
            lambda line: (-abs(line.balance), -line.debit, line.account_id)
        )
        self.assertRecordValues(
            cb_lines,
            [
                {
                    "debit": 100.0,
                    "credit": 0.0,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 100.0,
                    "tax_tag_ids": self.tax_tags[0].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 33.33,
                    "credit": 0.0,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 33.33,
                    "tax_tag_ids": self.tax_tags[1].ids,
                    "account_id": self.tax_account_1.id,
                },
            ],
        )

        cb_lines = tax_cash_basis_moves[1].line_ids.sorted(
            lambda line: (-abs(line.balance), -line.debit, line.account_id)
        )
        self.assertRecordValues(
            cb_lines,
            [
                {
                    "debit": 100.0,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[2].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 100.0,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 33.33,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[3].ids,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 33.33,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
            ],
        )

    def test_reconcile_cash_basis_tax_grid_reversal(self):
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "date": "2016-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 1000.0,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        },
                    )
                ],
            }
        )
        invoice.action_post()

        self.assertRecordValues(
            invoice.line_ids.sorted("balance"),
            [
                {
                    "debit": 0.0,
                    "credit": 1000.0,
                    "tax_tag_ids": [],
                    "account_id": self.company_data["default_account_revenue"].id,
                },
                {
                    "debit": 0.0,
                    "credit": 333.33,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 1333.33,
                    "credit": 0.0,
                    "tax_tag_ids": [],
                    "account_id": self.company_data["default_account_receivable"].id,
                },
            ],
        )

        reversal_wizard = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "reason": "test_reconcile_cash_basis_tax_grid_reversal",
                    "journal_id": invoice.journal_id.id,
                }
            )
        )
        refund = self.env["account.move"].browse(
            reversal_wizard.refund_moves()["res_id"]
        )
        refund.action_post()

        self.assertRecordValues(
            refund.line_ids.sorted("balance"),
            [
                {
                    "debit": 0.0,
                    "credit": 1333.33,
                    "tax_tag_ids": [],
                    "account_id": self.company_data["default_account_receivable"].id,
                },
                {
                    "debit": 333.33,
                    "credit": 0.0,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 1000.0,
                    "credit": 0.0,
                    "tax_tag_ids": [],
                    "account_id": self.company_data["default_account_revenue"].id,
                },
            ],
        )

        reversal_wizard = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=refund.ids)
            .create(
                {
                    "reason": "test_reconcile_cash_basis_tax_grid_reversal",
                    "journal_id": refund.journal_id.id,
                }
            )
        )
        reversed_refund = self.env["account.move"].browse(
            reversal_wizard.refund_moves()["res_id"]
        )

        self.assertRecordValues(
            reversed_refund.line_ids.sorted("balance"),
            [
                {
                    "debit": 0.0,
                    "credit": 1000.0,
                    "tax_tag_ids": [],
                    "account_id": self.company_data["default_account_revenue"].id,
                },
                {
                    "debit": 0.0,
                    "credit": 333.33,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 1333.33,
                    "credit": 0.0,
                    "tax_tag_ids": [],
                    "account_id": self.company_data["default_account_receivable"].id,
                },
            ],
        )

    def test_reconcile_cash_basis_tax_grid_multi_taxes(self):
        self.env.company.account_config_id.tax_exigibility = True
        base_taxes = (
            self.cash_basis_tax_a_third_amount + self.cash_basis_tax_tiny_amount
        )
        base_tags = self.tax_tags[0] + self.tax_tags[4]

        invoice_move = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "move_type": "entry",
                    "date": "2016-01-01",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "tax_ids": [(6, 0, base_taxes.ids)],
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 33.33,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 0.01,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": self.cash_basis_tax_tiny_amount.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 133.34,
                                "credit": 0.0,
                                "account_id": self.extra_receivable_account_1.id,
                            },
                        ),
                    ],
                }
            )
        )

        payment_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2017-01-01",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 133.34,
                            "account_id": self.extra_receivable_account_1.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 133.34,
                            "credit": 0.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )

        (invoice_move + payment_move).action_post()

        receivable_lines = (invoice_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()
        tax_cash_basis_moves = self._get_caba_moves(receivable_lines.move_id)

        self.assertFullReconcile(receivable_lines.full_reconcile_id, receivable_lines)
        self.assertEqual(len(tax_cash_basis_moves), 1)

        self.assertRecordValues(
            tax_cash_basis_moves.line_ids,
            [
                {
                    "debit": 100.0,
                    "credit": 0.0,
                    "tax_ids": [],
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 100.0,
                    "tax_ids": base_taxes.ids,
                    "tax_tag_ids": base_tags.ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 33.33,
                    "credit": 0.0,
                    "tax_ids": [],
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 33.33,
                    "tax_ids": [],
                    "tax_tag_ids": self.tax_tags[1].ids,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "tax_ids": [],
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "tax_ids": [],
                    "tax_tag_ids": self.tax_tags[5].ids,
                    "account_id": self.tax_account_2.id,
                },
            ],
        )

    def test_matching_number_full_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, "2016-01-01")
        line_b = self.create_line_for_reconciliation(
            -1000, -1000, currency, "2016-01-01"
        )
        (line_a + line_b).reconcile()
        self.assertFullReconcile(line_a.full_reconcile_id, (line_a + line_b))
        self.assertEqual(line_a.matching_number, str(line_a.full_reconcile_id.id))
        self.assertEqual(line_a.matching_number, line_b.matching_number)

    def test_partial_reconcile_rejects_invalid_structure(self):
        currency = self.env.company.currency_id
        debit_line = self.create_line_for_reconciliation(
            1000, 1000, currency, "2016-01-01"
        )
        credit_line = self.create_line_for_reconciliation(
            -1000, -1000, currency, "2016-01-01"
        )
        valid_vals = {
            "debit_move_id": debit_line.id,
            "credit_move_id": credit_line.id,
            "amount": 1000,
            "debit_amount_currency": 1000,
            "credit_amount_currency": 1000,
        }

        for invalid_vals in (
            {"credit_move_id": debit_line.id},
            {"amount": -1},
            {"debit_amount_currency": -1},
            {"credit_amount_currency": -1},
            {
                "amount": 0,
                "debit_amount_currency": 0,
                "credit_amount_currency": 0,
            },
        ):
            with (
                self.subTest(invalid_vals=invalid_vals),
                self.assertRaises(CheckViolation),
            ):
                self.env["account.partial.reconcile"].create(valid_vals | invalid_vals)

        with self.assertRaises(ValidationError):
            self.env["account.partial.reconcile"].create(
                valid_vals
                | {
                    "debit_move_id": credit_line.id,
                    "credit_move_id": debit_line.id,
                }
            )

        other_account_credit_line = self.create_line_for_reconciliation(
            -1000,
            -1000,
            currency,
            "2016-01-01",
            self.extra_receivable_account_1,
        )
        with self.assertRaises(ValidationError):
            self.env["account.partial.reconcile"].create(
                valid_vals | {"credit_move_id": other_account_credit_line.id}
            )

        partial = self.env["account.partial.reconcile"].create(valid_vals)
        for field_name, invalid_value in (
            ("amount", "NaN"),
            ("debit_amount_currency", "Infinity"),
            ("credit_amount_currency", "Infinity"),
        ):
            with self.subTest(field_name=field_name), self.assertRaises(CheckViolation):
                self.env.cr.execute(
                    SQL(
                        "UPDATE account_partial_reconcile SET %s = %s WHERE id = %s",
                        SQL.identifier(field_name),
                        invalid_value,
                        partial.id,
                    )
                )
        other_company = self.env["res.company"].create({"name": "Other Company"})
        with self.assertRaises(ValidationError):
            partial.company_id = other_company
        partial.unlink()

    def test_draft_caba_move_vals_round_trips_as_a_json_object(self):
        cash_basis_move, payment_move = self._prepare_cash_basis_move_and_payment()
        (cash_basis_move + payment_move).action_post()
        receivable_lines = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()
        partial = (
            receivable_lines.matched_debit_ids | receivable_lines.matched_credit_ids
        )[0]
        self.env.flush_all()

        self.env.cr.execute(
            "SELECT jsonb_typeof(draft_caba_move_vals) "
            "FROM account_partial_reconcile WHERE id = %s",
            (partial.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], "object")
        self.assertIsInstance(partial.draft_caba_move_vals, dict)
        self.assertFalse(partial._has_outdated_draft_caba_move_vals())

    def test_draft_caba_move_vals_reads_legacy_serialized_rows(self):
        cash_basis_move, payment_move = self._prepare_cash_basis_move_and_payment()
        (cash_basis_move + payment_move).action_post()
        receivable_lines = (cash_basis_move + payment_move).line_ids.filtered(
            lambda line: line.account_id == self.extra_receivable_account_1
        )
        receivable_lines.reconcile()
        partial = (
            receivable_lines.matched_debit_ids | receivable_lines.matched_credit_ids
        )[0]
        self.env.flush_all()
        partial.draft_caba_move_vals = json.dumps(partial.draft_caba_move_vals)
        self.env.flush_all()
        partial.invalidate_recordset(["draft_caba_move_vals"])
        self.env.cr.execute(
            "SELECT jsonb_typeof(draft_caba_move_vals) "
            "FROM account_partial_reconcile WHERE id = %s",
            (partial.id,),
        )
        self.assertEqual(self.env.cr.fetchone()[0], "string")
        self.assertFalse(partial._has_outdated_draft_caba_move_vals())

    def test_get_to_update_payments_reads_the_payment_side_amount(self):
        company_currency = self.env.company.currency_id
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2017-01-01",
                "date": "2017-01-01",
                "currency_id": company_currency.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "line",
                            "quantity": 1,
                            "price_unit": 100.0,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        invoice.action_post()
        payment = self._create_payment_without_outstanding_account(
            invoice,
            currency_id=self.other_currency.id,
            payment_date="2017-01-01",
        )

        receivable_lines = (invoice + payment.move_id).line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        partials = (
            receivable_lines.matched_debit_ids | receivable_lines.matched_credit_ids
        )
        self.assertRecordValues(
            partials,
            [{"debit_amount_currency": 100.0, "credit_amount_currency": 200.0}],
        )
        self.assertEqual(
            partials._get_to_update_payments(from_state="paid"),
            payment,
        )

    def _create_payment_without_outstanding_account(self, invoices, **wizard_vals):
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoices.ids)
            .create(wizard_vals)
            ._create_payments()
        )
        self.env.flush_all()
        self.env.cr.execute(
            SQL(
                "UPDATE account_payment SET outstanding_account_id = NULL WHERE id = %s",
                payment.id,
            )
        )
        payment.invalidate_recordset(["outstanding_account_id"])
        self.assertFalse(payment.outstanding_account_id)
        self.assertTrue(payment.move_id)
        return payment

    def _create_grouped_payment_without_outstanding_account(self):
        invoices = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": "2016-01-01",
                    "date": "2016-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "line",
                                "quantity": 1,
                                "price_unit": amount,
                                "tax_ids": [],
                            }
                        )
                    ],
                }
                for amount in (50.0, 50.0)
            ]
        )
        invoices.action_post()
        payment = self._create_payment_without_outstanding_account(
            invoices, group_payment=True
        )
        receivable_lines = (invoices + payment.move_id).line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        )
        return payment, receivable_lines

    def test_unreconcile_grouped_payment_returns_to_in_process(self):
        payment, receivable_lines = (
            self._create_grouped_payment_without_outstanding_account()
        )
        self.assertEqual(payment.state, "paid")
        receivable_lines.remove_move_reconcile()
        payment.invalidate_recordset(["state"])
        self.assertEqual(payment.state, "in_process")

    def test_get_to_update_payments_is_stable_under_duplicates(self):
        payment, receivable_lines = (
            self._create_grouped_payment_without_outstanding_account()
        )
        partials = (
            receivable_lines.matched_debit_ids | receivable_lines.matched_credit_ids
        )
        duplicated = partials.browse(partials.ids + partials.ids)
        self.assertEqual(
            partials._get_to_update_payments(from_state="paid"),
            payment,
        )
        self.assertEqual(
            duplicated._get_to_update_payments(from_state="paid"),
            payment,
        )

    def test_one_full_reconcile_per_group_when_an_exchange_difference_is_created(self):
        currency = self.other_currency
        debit_line = self.create_line_for_reconciliation(
            1200.0, 3600.0, currency, "2016-01-01"
        )
        credit_line = self.create_line_for_reconciliation(
            -1800.0, -3600.0, currency, "2017-01-01"
        )
        before = self.env["account.full.reconcile"].search([])

        (debit_line + credit_line).reconcile()

        created = self.env["account.full.reconcile"].search([]) - before
        self.assertTrue(
            (debit_line + credit_line).matched_debit_ids.exchange_move_id
            | (debit_line + credit_line).matched_credit_ids.exchange_move_id,
            "the fixture must produce an exchange difference for this to test anything",
        )
        self.assertEqual(len(created), 1, "one reconciliation, one full reconcile")
        self.assertFalse(
            self.env["account.full.reconcile"]
            .search([])
            .filtered(lambda full: not full.reconciled_line_ids),
            "no full reconcile should be left without lines",
        )

    def test_matching_number_invariants_hold_after_the_raw_sql_write(self):
        currency = self.env.company.currency_id
        full_a = self.create_line_for_reconciliation(1000, 1000, currency, "2016-01-01")
        full_b = self.create_line_for_reconciliation(
            -1000, -1000, currency, "2016-01-01"
        )
        chain = [
            self.create_line_for_reconciliation(amount, amount, currency, "2016-01-01")
            for amount in (100, -60, -200, 50)
        ]
        lonely = self.create_line_for_reconciliation(700, 700, currency, "2016-01-01")
        (full_a + full_b).reconcile()
        (chain[0] + chain[1]).reconcile()
        (chain[0] + chain[2]).reconcile()
        (chain[3] + chain[2]).reconcile()

        involved = full_a + full_b + lonely
        for line in chain:
            involved |= line
        involved._constrains_matching_number()
        self.assertEqual(full_a.matching_number, str(full_a.full_reconcile_id.id))
        self.assertEqual(len({line.matching_number for line in chain}), 1)
        self.assertTrue(chain[0].matching_number.startswith("P"))
        self.assertFalse(lonely.matching_number)

        (full_a + full_b).remove_move_reconcile()
        chain[0].remove_move_reconcile()
        involved.exists()._constrains_matching_number()

    def test_matching_number_partial_single_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, "2016-01-01")
        line_b = self.create_line_for_reconciliation(-500, -500, currency, "2016-01-01")
        (line_a + line_b).reconcile()
        self.assertEqual(line_a.matching_number, f"P{line_a.matched_credit_ids.id}")
        self.assertEqual(line_a.matching_number, line_b.matching_number)

    def test_unlink_reverses_a_shared_exchange_move_once(self):
        currency = self.env.company.currency_id
        debit_line = self.create_line_for_reconciliation(
            1000, 1000, currency, "2016-01-01"
        )
        credit_lines = self.create_line_for_reconciliation(
            -500, -500, currency, "2016-01-01"
        ) + self.create_line_for_reconciliation(-500, -500, currency, "2016-01-01")
        exchange_move = debit_line.move_id
        partials = self.env["account.partial.reconcile"].create(
            [
                {
                    "amount": 500,
                    "debit_amount_currency": 500,
                    "credit_amount_currency": 500,
                    "debit_move_id": debit_line.id,
                    "credit_move_id": credit_line.id,
                    "exchange_move_id": exchange_move.id,
                }
                for credit_line in credit_lines
            ]
        )
        partials.unlink()

        self.assertEqual(len(exchange_move.reversal_move_ids), 1)

    def test_matching_number_partial_multi_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, "2016-01-01")
        line_b = self.create_line_for_reconciliation(-500, -500, currency, "2016-01-01")
        line_c = self.create_line_for_reconciliation(
            -1000, -1000, currency, "2016-01-01"
        )
        line_d = self.create_line_for_reconciliation(1000, 1000, currency, "2016-01-01")
        (line_a + line_b).reconcile()
        (line_a + line_c).reconcile()
        (line_c + line_d).reconcile()
        self.assertEqual(line_a.matching_number, f"P{line_a.matched_credit_ids.ids[0]}")
        self.assertEqual(line_b.matching_number, line_a.matching_number)
        self.assertEqual(line_c.matching_number, line_a.matching_number)
        self.assertEqual(line_d.matching_number, line_a.matching_number)

        line_b.remove_move_reconcile()
        self.assertEqual(line_a.matching_number, f"P{line_a.matched_credit_ids.ids[0]}")
        self.assertEqual(line_b.matching_number, False)
        self.assertEqual(line_c.matching_number, f"P{line_c.matched_debit_ids.ids[0]}")
        self.assertEqual(line_d.matching_number, line_c.matching_number)

        (line_a + line_b).reconcile()
        self.assertEqual(line_a.matching_number, line_c.matching_number)
        self.assertEqual(line_b.matching_number, line_c.matching_number)
        self.assertEqual(line_c.matching_number, f"P{line_c.matched_debit_ids.ids[0]}")
        self.assertEqual(line_d.matching_number, line_c.matching_number)

    def test_matching_number_partial_multi_separate_reconcile(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(1000, 1000, currency, "2016-01-01")
        line_b = self.create_line_for_reconciliation(-500, -500, currency, "2016-01-01")
        (line_a + line_b).reconcile()
        self.assertEqual(line_a.matching_number, f"P{line_a.matched_credit_ids.id}")
        self.assertEqual(line_a.matching_number, line_b.matching_number)

        line_c = self.create_line_for_reconciliation(-300, -300, currency, "2016-01-01")
        (line_a + line_c).reconcile()
        self.assertEqual(line_a.matching_number, f"P{line_a.matched_credit_ids.ids[0]}")
        self.assertEqual(line_a.matching_number, line_b.matching_number)
        self.assertEqual(line_a.matching_number, line_c.matching_number)

    def test_matching_number_unreconcile_single(self):
        currency = self.env.company.currency_id
        full_line_a = self.create_line_for_reconciliation(
            200, 200, currency, "2016-01-01"
        )
        full_line_b = self.create_line_for_reconciliation(
            -200, -200, currency, "2016-01-01"
        )
        partial_line_a = self.create_line_for_reconciliation(
            1000, 1000, currency, "2016-01-01"
        )
        partial_line_b = self.create_line_for_reconciliation(
            -500, -500, currency, "2016-01-01"
        )
        (full_line_a + full_line_b).reconcile()
        (partial_line_a + partial_line_b).reconcile()
        (
            full_line_a + full_line_b + partial_line_a + partial_line_b
        ).remove_move_reconcile()
        self.assertFalse(full_line_a.matching_number)
        self.assertFalse(full_line_b.matching_number)
        self.assertFalse(partial_line_a.matching_number)
        self.assertFalse(partial_line_b.matching_number)

    def test_matching_number_unreconcile_multi(self):
        currency = self.env.company.currency_id
        line_a = self.create_line_for_reconciliation(-500, -500, currency, "2016-01-01")
        line_b = self.create_line_for_reconciliation(1000, 1000, currency, "2016-01-01")
        line_c = self.create_line_for_reconciliation(
            -1000, -1000, currency, "2016-01-01"
        )
        line_d = self.create_line_for_reconciliation(300, 300, currency, "2016-01-01")
        (line_a + line_b).reconcile()
        (line_b + line_c).reconcile()
        (line_c + line_d).reconcile()

        previous_matching_number = line_a.matching_number
        line_a.remove_move_reconcile()
        self.assertFalse(line_a.matching_number)
        self.assertNotEqual(previous_matching_number, line_b.matching_number)
        self.assertEqual(line_b.matching_number, line_c.matching_number)
        self.assertEqual(line_b.matching_number, line_d.matching_number)

        previous_matching_number = line_b.matching_number
        line_b.remove_move_reconcile()
        self.assertFalse(line_b.matching_number)
        self.assertNotEqual(previous_matching_number, line_c.matching_number)
        self.assertEqual(line_c.matching_number, line_d.matching_number)

        line_c.remove_move_reconcile()
        self.assertFalse(line_c.matching_number)
        self.assertFalse(line_d.matching_number)

    def test_matching_loop(self):
        currency = self.env.company.currency_id
        wrong_credit = self.create_line_for_reconciliation(
            -500, -500, currency, "2016-01-01"
        )
        debit_a = self.create_line_for_reconciliation(
            1000, 1000, currency, "2016-01-01"
        )
        debit_b = self.create_line_for_reconciliation(
            1000, 1000, currency, "2016-01-01"
        )
        credit_a = self.create_line_for_reconciliation(
            -1000, -1000, currency, "2016-01-01"
        )
        credit_b = self.create_line_for_reconciliation(
            -1000, -1000, currency, "2016-01-01"
        )
        all_lines = debit_a + debit_b + credit_a + credit_b
        (wrong_credit + debit_a).reconcile()
        (debit_a + credit_a).reconcile()
        wrong_credit.remove_move_reconcile()
        (credit_a + debit_b).reconcile()
        (debit_b + credit_b).reconcile()

        matching_number = f"P{debit_a.matched_credit_ids.ids[0]}"
        self.assertEqual(all_lines.mapped("matching_number"), [matching_number] * 4)
        self.assertEqual(all_lines.mapped("amount_residual"), [500, 0, 0, -500])

        (debit_a + credit_b).reconcile()
        matching_number = f"{debit_a.full_reconcile_id.id}"
        self.assertEqual(all_lines.mapped("matching_number"), [matching_number] * 4)
        self.assertEqual(all_lines.mapped("amount_residual"), [0, 0, 0, 0])

    def test_caba_mix_reconciliation(self):
        self.tax_account_1.reconcile = True
        self.env.company.account_config_id.tax_exigibility = True

        non_caba_tax = self.env["account.tax"].create(
            {
                "name": "tax 20%",
                "type_tax_use": "purchase",
                "company_ids": [Command.set(self.company_data["company"].ids)],
                "amount": 20,
                "tax_exigibility": "on_invoice",
                "invoice_repartition_line_ids": [
                    (0, 0, {"repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "repartition_type": "tax",
                            "account_id": self.tax_account_1.id,
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"repartition_type": "base"}),
                    (
                        0,
                        0,
                        {
                            "repartition_type": "tax",
                            "account_id": self.tax_account_1.id,
                        },
                    ),
                ],
            }
        )

        non_caba_inv = self.init_invoice(
            "in_invoice", amounts=[1000], post=True, taxes=non_caba_tax
        )

        caba_inv = self.init_invoice(
            "in_invoice",
            amounts=[300],
            post=True,
            taxes=self.cash_basis_tax_a_third_amount,
        )

        pmt_wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=caba_inv.ids)
            .create(
                {
                    "payment_date": caba_inv.date,
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "payment_channel_id": self.inbound_payment_channel.id,
                }
            )
        )
        pmt_wizard._create_payments()

        partial_rec = caba_inv.mapped("line_ids.matched_debit_ids")
        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_rec_id", "in", partial_rec.ids)]
        )

        misc_move = self.env["account.move"].create(
            {
                "name": "Misc move",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "line 1",
                            "account_id": self.tax_account_1.id,
                            "credit": 300,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "line 2",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 300,
                        },
                    ),
                ],
            }
        )

        misc_move.action_post()

        lines_to_reconcile = (
            (misc_move + caba_move + non_caba_inv)
            .mapped("line_ids")
            .filtered(lambda x: x.account_id == self.tax_account_1)
        )
        lines_to_reconcile.reconcile()

        self.assertTrue(
            all(line.full_reconcile_id for line in lines_to_reconcile),
            "All tax lines should be fully reconciled",
        )

    def test_caba_double_tax_negative_line(self):
        self.env.company.account_config_id.tax_exigibility = True
        invoice = self.init_invoice(
            "in_invoice",
            amounts=[300, -60],
            post=True,
            taxes=self.cash_basis_tax_a_third_amount,
        )

        pmt_wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "amount": 320,
                    "payment_date": invoice.date,
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "payment_channel_id": self.inbound_payment_channel.id,
                }
            )
        )

        pmt_wizard._create_payments()

        partial_rec = invoice.mapped("line_ids.matched_debit_ids")
        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_rec_id", "in", partial_rec.ids)]
        )

        self.assertRecordValues(
            caba_move.line_ids.sorted(
                lambda line: (-abs(line.balance), -line.debit, line.account_id)
            ),
            [
                {
                    "debit": 240.0,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[0].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 240.0,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 80.0,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[1].ids,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 80.0,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
            ],
        )

    def test_caba_dest_acc_reconciliation_partial_pmt(self):
        self.tax_account_1.reconcile = True
        self.env.company.account_config_id.tax_exigibility = True

        caba_inv = self.init_invoice(
            "in_invoice",
            amounts=[900],
            post=True,
            taxes=self.cash_basis_tax_a_third_amount,
        )

        pmt_wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=caba_inv.ids)
            .create(
                {
                    "amount": 600,
                    "payment_date": caba_inv.date,
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "payment_channel_id": self.inbound_payment_channel.id,
                }
            )
        )
        pmt_wizard._create_payments()

        partial_rec = caba_inv.mapped("line_ids.matched_debit_ids")
        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_rec_id", "in", partial_rec.ids)]
        )

        misc_move = self.env["account.move"].create(
            {
                "name": "Misc move",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "line 1",
                            "account_id": self.tax_account_1.id,
                            "credit": 150,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "line 2",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 150,
                        },
                    ),
                ],
            }
        )

        misc_move.action_post()

        lines_to_reconcile = (
            (misc_move + caba_move)
            .mapped("line_ids")
            .filtered(lambda x: x.account_id == self.tax_account_1)
        )
        lines_to_reconcile.reconcile()

        self.assertTrue(
            all(line.full_reconcile_id for line in lines_to_reconcile),
            "All tax lines should be fully reconciled",
        )

    def test_caba_undo_reconciliation(self):
        self.env.company.account_config_id.tax_exigibility = True

        bill = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-01",
                "date": "2019-01-01",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "line",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "price_unit": 1000.0,
                            "tax_ids": [(6, 0, self.cash_basis_tax_a_third_amount.ids)],
                        },
                    )
                ],
            }
        )
        bill.action_post()

        payment = (
            self.env["account.payment.register"]
            .with_context(active_ids=bill.ids, active_model="account.move")
            .create({})
            ._create_payments()
        )

        init_reconciliation = (payment.move_id + bill).line_ids._reconciled_by_number()
        self.assertEqual(len(init_reconciliation), 2)

        bill.action_draft()
        self.assertEqual(
            (payment.move_id + bill).line_ids._reconciled_by_number(),
            init_reconciliation,
        )

        bill.line_ids.remove_move_reconcile()
        self.assertFalse((payment.move_id + bill).line_ids._reconciled_by_number())

    def test_caba_foreign_vat(self):
        self.env.company.account_config_id.tax_exigibility = True

        test_country = self.env["res.country"].create(
            {
                "name": "Bretonnia",
                "code": "wh",
            }
        )

        foreign_vat_fpos = self.env["account.fiscal.position"].create(
            {
                "name": "Fiscal Position to the Holy Grail",
                "country_id": test_country.id,
                "foreign_vat": "WH1234",
            }
        )

        self.env["account.tax.group"].create(
            {
                "name": "tax_group",
                "country_id": test_country.id,
            }
        )

        foreign_caba_tax = self.env["account.tax"].create(
            {
                "name": "foreign tax_1",
                "amount": 33.3333,
                "company_ids": [Command.set(self.company_data["company"].ids)],
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "tax_exigibility": "on_payment",
                "country_id": test_country.id,
                "invoice_repartition_line_ids": [
                    (0, 0, {"repartition_type": "base"}),
                    (0, 0, {"repartition_type": "tax"}),
                ],
                "refund_repartition_line_ids": [
                    (0, 0, {"repartition_type": "base"}),
                    (0, 0, {"repartition_type": "tax"}),
                ],
            }
        )

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2021-07-01",
                "fiscal_position_id": foreign_vat_fpos.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "test",
                            "price_unit": 100,
                            "tax_ids": [Command.set(foreign_caba_tax.ids)],
                        }
                    ),
                ],
            }
        )
        invoice.action_post()

        self.env["account.payment.register"].with_context(
            active_ids=invoice.ids, active_model="account.move"
        ).create(
            {
                "payment_date": invoice.date,
            }
        )._create_payments()

        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_origin_move_id", "=", invoice.id)]
        )

        self.assertEqual(
            caba_move.fiscal_position_id,
            foreign_vat_fpos,
            "The foreign VAT fiscal position should be kept in the cash basis move.",
        )

    def test_caba_tax_group(self):
        self.env.company.account_config_id.tax_exigibility = True

        self.tax_account_1.reconcile = True

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        move_form.invoice_date = fields.Date.from_string("2019-01-01")
        move_form.partner_id = self.partner_a

        tax_a = self.cash_basis_tax_a_third_amount
        tax_b = self.cash_basis_tax_tiny_amount

        tax_group = self.env["account.tax"].create(
            {
                "name": "tax group",
                "amount_type": "group",
                "company_ids": [Command.set(self.company_data["company"].ids)],
                "children_tax_ids": [Command.set([tax_a.id, tax_b.id])],
            }
        )

        invoice = (
            self.env["account.move"]
            .with_context(skip_invoice_sync=True)
            .create(
                {
                    "partner_id": self.partner_a.id,
                    "invoice_date": fields.Date.from_string("2019-01-01"),
                    "move_type": "entry",
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 3000.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                                "tax_ids": [Command.set(tax_group.ids)],
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 1000.0,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": tax_a.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 1.0,
                                "account_id": self.cash_basis_transfer_account.id,
                                "tax_repartition_line_id": tax_b.invoice_repartition_line_ids.filtered(
                                    lambda line: line.repartition_type == "tax"
                                ).id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 4001.0,
                                "credit": 0.0,
                                "account_id": self.extra_receivable_account_1.id,
                            }
                        ),
                    ],
                }
            )
        )

        invoice.action_post()

        pmt_wizard = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({})
        )
        pmt_wizard._create_payments()

        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_origin_move_id", "=", invoice.id)]
        )
        self.assertEqual(len(caba_move.line_ids), 6, "All lines should be there")
        tax_group_base_tags = (
            (tax_a | tax_b)
            .invoice_repartition_line_ids.filtered(
                lambda l: l.repartition_type == "base"
            )
            .tag_ids.ids
        )
        tax_a_tax_tag = tax_a.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        ).tag_ids.ids
        tax_b_tax_tag = tax_b.invoice_repartition_line_ids.filtered(
            lambda l: l.repartition_type == "tax"
        ).tag_ids.ids
        self.assertRecordValues(
            caba_move.line_ids,
            [
                {
                    "balance": 3000.0,
                    "tax_line_id": False,
                    "tax_tag_ids": [],
                    "tax_ids": [],
                },
                {
                    "balance": -3000.0,
                    "tax_line_id": False,
                    "tax_tag_ids": tax_group_base_tags,
                    "tax_ids": (tax_a | tax_b).ids,
                },
                {
                    "balance": 1000.0,
                    "tax_line_id": False,
                    "tax_tag_ids": [],
                    "tax_ids": [],
                },
                {
                    "balance": -1000.0,
                    "tax_line_id": tax_a.id,
                    "tax_tag_ids": tax_a_tax_tag,
                    "tax_ids": [],
                },
                {
                    "balance": 1.0,
                    "tax_line_id": False,
                    "tax_tag_ids": [],
                    "tax_ids": [],
                },
                {
                    "balance": -1.0,
                    "tax_line_id": tax_b.id,
                    "tax_tag_ids": tax_b_tax_tag,
                    "tax_ids": [],
                },
            ],
        )

    def test_cash_basis_taxline_without_account(self):
        self.env.company.account_config_id.tax_exigibility = True

        tax = self.env["account.tax"].create(
            {
                "name": "cash basis 20%",
                "type_tax_use": "purchase",
                "amount": 20,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "invoice_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 40,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 60,
                            "repartition_type": "tax",
                        },
                    ),
                ],
                "refund_repartition_line_ids": [
                    (
                        0,
                        0,
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 40,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "factor_percent": 60,
                            "repartition_type": "tax",
                        },
                    ),
                ],
            }
        )

        move_form = Form(
            self.env["account.move"].with_context(default_move_type="in_invoice")
        )
        move_form.partner_id = self.partner_a
        move_form.invoice_date = fields.Date.from_string("2017-01-01")
        with move_form.invoice_line_ids.new() as line_form:
            line_form.product_id = self.product_a
            line_form.tax_ids.clear()
            line_form.tax_ids.add(tax)
        invoice = move_form.save()
        invoice.action_post()

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create(
            {
                "payment_date": invoice.date,
            }
        )._create_payments()

        partial_rec = invoice.mapped("line_ids.matched_debit_ids")
        caba_move = self.env["account.move"].search(
            [("tax_cash_basis_rec_id", "=", partial_rec.id)]
        )
        expected_values = [
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 0.0,
                "credit": 800.0,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 800.0,
                "credit": 0.0,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 0.0,
                "credit": 64.0,
            },
            {"account_id": self.tax_account_1.id, "debit": 64.0, "credit": 0.0},
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 0.0,
                "credit": 96.0,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 96.0,
                "credit": 0.0,
            },
        ]
        self.assertRecordValues(caba_move.line_ids, expected_values)

    def test_cash_basis_full_refund(self):
        self.env.company.account_config_id.tax_exigibility = True

        tax = self.env["account.tax"].create(
            {
                "name": "cash basis 20%",
                "type_tax_use": "purchase",
                "amount": 20,
                "tax_exigibility": "on_payment",
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
            }
        )

        invoice = self.init_invoice(
            "out_invoice", post=True, amounts=[1000.0], taxes=tax
        )

        credit_note_wizard = (
            self.env["account.move.reversal"]
            .with_context({"active_ids": invoice.ids, "active_model": "account.move"})
            .create(
                {
                    "reason": "test_cash_basis_full_refund",
                    "journal_id": invoice.journal_id.id,
                }
            )
        )
        action_values = credit_note_wizard.modify_moves()
        self.assertRecordValues(invoice, [{"payment_state": "reversed"}])

        cash_basis_moves = self.env["account.move"].search(
            [
                (
                    "tax_cash_basis_origin_move_id",
                    "in",
                    (invoice.id, action_values["res_id"]),
                )
            ]
        )
        self.assertFalse(cash_basis_moves)

        caba_transfer_amls = self.env["account.move.line"].search(
            [
                ("account_id", "=", self.cash_basis_transfer_account.id),
                ("move_id.move_type", "=", "entry"),
            ]
        )
        self.assertFalse(caba_transfer_amls.move_id)

    def test_reconcile_import(self):
        comp_curr = self.company_data["currency"]

        line_1 = self.create_line_for_reconciliation(
            1000.0, 1000.0, comp_curr, "2016-01-01"
        )
        line_1.move_id.action_draft()
        line_2 = self.create_line_for_reconciliation(
            -300.0, -300.0, comp_curr, "2016-01-01"
        )
        line_3 = self.create_line_for_reconciliation(
            -400.0, -400.0, comp_curr, "2016-01-01"
        )
        line_4 = self.create_line_for_reconciliation(
            -500.0, -500.0, comp_curr, "2016-01-01"
        )
        line_4.move_id.action_draft()
        line_5 = self.create_line_for_reconciliation(
            200.0, 200.0, comp_curr, "2016-01-01"
        )
        (line_1 + line_2 + line_3).matching_number = "11111"
        (line_4 + line_5).matching_number = "22222"
        (line_1 + line_4).move_id.action_post()
        self.assertRegex(line_1.matching_number, r"^P\d+")
        self.assertRegex(line_4.matching_number, r"^P\d+")
        (line_1 + line_4).reconcile()
        self.assertRegex(line_1.matching_number, r"^\d+")
        self.assertTrue(line_1.full_reconcile_id)

    def test_reconcile_import_same_matching_different_account(self):
        comp_curr = self.company_data["currency"]

        line_1 = self.create_line_for_reconciliation(
            100.0, 100.0, comp_curr, "2016-01-01", self.receivable_account
        )
        line_2 = self.create_line_for_reconciliation(
            -100.0, -100.0, comp_curr, "2016-01-01", self.receivable_account
        )
        line_3 = self.create_line_for_reconciliation(
            200.0, 200.0, comp_curr, "2016-01-01", self.extra_receivable_account_1
        )
        line_4 = self.create_line_for_reconciliation(
            -200.0, -200.0, comp_curr, "2016-01-01", self.extra_receivable_account_1
        )
        (line_1 + line_2 + line_3 + line_4).move_id.action_draft()
        (line_1 + line_2 + line_3 + line_4).matching_number = "11111"
        (line_1 + line_2).move_id.action_post()
        self.assertRegex(line_1.matching_number, r"^\d+")
        self.assertTrue(line_1.full_reconcile_id)
        self.assertEqual(line_3.matching_number, "I11111")
        (line_3 + line_4).move_id.action_post()
        self.assertTrue(line_3.full_reconcile_id)

    def test_reconcile_payment_custom_rate(self):
        company_currency = self.company_data["currency"]
        foreign_currency = self.other_currency

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2017-01-01",
                "date": "2017-01-01",
                "partner_id": self.partner_a.id,
                "currency_id": company_currency.id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "price_unit": 400.0,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        payment = self.env["account.payment"].create(
            {
                "date": invoice.date,
                "amount": 800.0,
                "currency_id": foreign_currency.id,
                "partner_id": self.partner_a.id,
            }
        )
        payment.action_post()
        self.env["res.currency.rate"].search(
            [("currency_id", "=", foreign_currency.id)]
        ).unlink()

        lines_to_reconcile = (invoice + payment.move_id).line_ids.filtered(
            lambda x: x.account_id.account_type == "asset_receivable"
        )
        lines_to_reconcile.reconcile()

        self.assertTrue(
            all(lines_to_reconcile.mapped("reconciled")),
            "All lines should be fully reconciled",
        )

    def test_reconcile_payment_with_no_exchange_diff_journal(self):
        self.env.company.account_config_id.currency_exchange_journal_id = False

        move_vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "currency_id": self.other_currency.id,
            "invoice_line_ids": [
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "price_unit": 1000.0,
                        "tax_ids": [],
                    }
                ),
            ],
        }

        payment_vals = {
            "currency_id": self.other_currency.id,
            "payment_difference_handling": "reconcile",
            "writeoff_account_id": self.env.company.account_config_id.expense_currency_exchange_account_id.id,
        }

        invoice_no_diff = self.env["account.move"].create(
            {**move_vals, "date": "2017-01-01", "invoice_date": "2017-01-01"}
        )
        invoice_no_diff.action_post()
        wizard_no_diff = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice_no_diff.ids)
            .create({**payment_vals, "payment_date": "2017-01-01", "amount": 3000})
        )
        wizard_no_diff._create_payments()

        invoice_diff = self.env["account.move"].create(
            {**move_vals, "date": "2016-01-01", "invoice_date": "2016-01-01"}
        )
        invoice_diff.action_post()
        wizard_diff = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice_diff.ids)
            .create({**payment_vals, "payment_date": "2018-01-01", "amount": 2000})
        )
        with self.assertRaises(UserError):
            wizard_diff._create_payments()

    def test_cash_basis_with_analytic_distribution(self):
        self.env.company.account_config_id.tax_exigibility = True

        analytic_plan = self.env["account.analytic.plan"].create(
            {
                "name": "Default",
            }
        )
        analytic_account_a = self.env["account.analytic.account"].create(
            {
                "name": "analytic_account_a",
                "plan_id": analytic_plan.id,
                "company_id": False,
            }
        )
        analytic_account_b = self.env["account.analytic.account"].create(
            {
                "name": "analytic_account_b",
                "plan_id": analytic_plan.id,
                "company_id": False,
            }
        )
        analytic_distribution_a = {
            analytic_account_a.id: 100,
        }
        analytic_distribution_b = {
            analytic_account_b.id: 100,
        }
        analytic_distribution_a_serialized = {
            str(analytic_account_a.id): 100,
        }
        analytic_distribution_b_serialized = {
            str(analytic_account_b.id): 100,
        }

        tax = self.env["account.tax"].create(
            {
                "name": "cash basis 20%",
                "type_tax_use": "purchase",
                "amount": 20,
                "tax_exigibility": "on_payment",
                "analytic": False,
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
            }
        )

        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "date": "2017-01-01",
                    "invoice_date": "2017-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "price_unit": 100.0,
                                "tax_ids": [Command.set(tax.ids)],
                                "analytic_distribution": analytic_distribution_a,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.product_b.id,
                                "price_unit": 100.0,
                                "tax_ids": [Command.set(tax.ids)],
                                "analytic_distribution": analytic_distribution_b,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.product_b.id,
                                "price_unit": 100.0,
                                "tax_ids": [Command.set(tax.ids)],
                                "analytic_distribution": analytic_distribution_b,
                            }
                        ),
                    ],
                }
            ]
        )
        invoice.action_post()

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create(
            {
                "payment_date": invoice.date,
            }
        )._create_payments()

        caba_move = invoice.tax_cash_basis_created_move_ids
        expected_caba_move_line_values = [
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 0.0,
                "credit": 100.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 100.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 0.0,
                "credit": 200.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 200.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.tax_account_1.id,
                "debit": 0.0,
                "credit": 18.0,
                "analytic_distribution": False,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 18.0,
                "credit": 0.0,
                "analytic_distribution": False,
            },
            {
                "account_id": self.tax_account_2.id,
                "debit": 0.0,
                "credit": 14.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 14.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.tax_account_2.id,
                "debit": 0.0,
                "credit": 28.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 28.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
        ]
        self.assertRecordValues(
            caba_move.line_ids.sorted("id").sorted("sequence"),
            expected_caba_move_line_values,
        )

    def test_cash_basis_with_analytic_distribution_analytic_tax(self):
        self.env.company.account_config_id.tax_exigibility = True

        analytic_plan = self.env["account.analytic.plan"].create(
            {
                "name": "Default",
            }
        )
        analytic_account_a = self.env["account.analytic.account"].create(
            {
                "name": "analytic_account_a",
                "plan_id": analytic_plan.id,
                "company_id": False,
            }
        )
        analytic_account_b = self.env["account.analytic.account"].create(
            {
                "name": "analytic_account_b",
                "plan_id": analytic_plan.id,
                "company_id": False,
            }
        )
        analytic_distribution_a = {
            analytic_account_a.id: 100,
        }
        analytic_distribution_b = {
            analytic_account_b.id: 100,
        }
        analytic_distribution_a_serialized = {
            str(analytic_account_a.id): 100,
        }
        analytic_distribution_b_serialized = {
            str(analytic_account_b.id): 100,
        }

        tax = self.env["account.tax"].create(
            {
                "name": "cash basis 20%",
                "type_tax_use": "purchase",
                "amount": 20,
                "tax_exigibility": "on_payment",
                "analytic": True,
                "cash_basis_transition_account_id": self.cash_basis_transfer_account.id,
                "invoice_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create(
                        {
                            "factor_percent": 100,
                            "repartition_type": "base",
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 30,
                            "account_id": self.tax_account_1.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": True,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 70,
                            "account_id": self.tax_account_2.id,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                ],
            }
        )

        invoice = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "date": "2017-01-01",
                    "invoice_date": "2017-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "price_unit": 100.0,
                                "tax_ids": [Command.set(tax.ids)],
                                "analytic_distribution": analytic_distribution_a,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.product_b.id,
                                "price_unit": 100.0,
                                "tax_ids": [Command.set(tax.ids)],
                                "analytic_distribution": analytic_distribution_b,
                            }
                        ),
                        Command.create(
                            {
                                "product_id": self.product_b.id,
                                "price_unit": 100.0,
                                "tax_ids": [Command.set(tax.ids)],
                                "analytic_distribution": analytic_distribution_b,
                            }
                        ),
                    ],
                }
            ]
        )
        invoice.action_post()

        self.env["account.payment.register"].with_context(
            active_model="account.move", active_ids=invoice.ids
        ).create(
            {
                "payment_date": invoice.date,
            }
        )._create_payments()

        caba_move = invoice.tax_cash_basis_created_move_ids
        expected_caba_move_line_values = [
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 0.0,
                "credit": 100.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 100.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 0.0,
                "credit": 200.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.cash_basis_base_account.id,
                "debit": 200.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.tax_account_1.id,
                "debit": 0.0,
                "credit": 6.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 6.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.tax_account_2.id,
                "debit": 0.0,
                "credit": 14.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 14.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_a_serialized,
            },
            {
                "account_id": self.tax_account_1.id,
                "debit": 0.0,
                "credit": 12.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 12.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.tax_account_2.id,
                "debit": 0.0,
                "credit": 28.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
            {
                "account_id": self.cash_basis_transfer_account.id,
                "debit": 28.0,
                "credit": 0.0,
                "analytic_distribution": analytic_distribution_b_serialized,
            },
        ]
        self.assertRecordValues(
            caba_move.line_ids.sorted("id").sorted("sequence"),
            expected_caba_move_line_values,
        )

    def test_partial_payments_auto_validation(self):
        self.company_data[
            "default_journal_bank"
        ].inbound_payment_channel_ids += self.env["account.payment.channel"].create(
            {
                "name": "Manual without outstanding",
                "payment_method_id": self.env.ref(
                    "account.account_payment_method_manual_in"
                ).id,
            }
        )
        with patch.object(
            self.env.registry["account.move"],
            "_get_invoice_in_payment_state",
            return_value="in_payment",
        ):

            def reconcile_move(
                move,
                transaction_amount,
                balance=None,
                date="2023-09-30",
                currency=None,
                lines_filter=None,
            ):
                lines_filter = lines_filter or (
                    lambda l: (
                        l.account_id.account_type
                        in ("asset_receivable", "liability_payable")
                    )
                )
                move_line = move.line_ids.filtered(lines_filter)[0]
                rec_account = move_line.account_id
                rec_line = self.create_line_for_reconciliation(
                    -(balance or transaction_amount),
                    -transaction_amount,
                    currency or move.currency_id,
                    date,
                    account_1=rec_account,
                )
                amls = rec_line + move_line
                amls.reconcile()

            vendor_bill = self.init_invoice(
                move_type="in_invoice", amounts=[1000], post=True
            )
            payment = self.create_move_payment(vendor_bill, 10)
            self.assertEqual(payment.state, "in_process")
            reconcile_move(vendor_bill, -12)
            self.assertEqual(payment.state, "in_process")
            reconcile_move(vendor_bill, -10)
            self.assertEqual(payment.state, "paid")

            customer_invoice = self.init_invoice(
                move_type="out_invoice", amounts=[400], post=True
            )
            payment1 = self.create_move_payment(customer_invoice, 200)
            self.assertEqual(payment1.state, "in_process")
            payment2 = self.create_move_payment(customer_invoice, 50)
            self.assertEqual(payment2.state, "in_process")
            payment3 = self.create_move_payment(customer_invoice, 10)
            self.assertEqual(payment3.state, "in_process")
            reconcile_move(customer_invoice, 50)
            self.assertEqual(payment1.state, "in_process")
            self.assertEqual(payment2.state, "paid")
            self.assertEqual(payment3.state, "in_process")

            foreign_currency = self.other_currency_2
            customer_invoice_foreign = self.init_invoice(
                move_type="out_invoice",
                amounts=[200],
                post=True,
                currency=foreign_currency,
            )
            payment1 = self.create_move_payment(customer_invoice_foreign, 30)
            self.assertEqual(payment1.state, "in_process")
            payment2 = self.create_move_payment(customer_invoice_foreign, 60)
            self.assertEqual(payment2.state, "in_process")
            payment3 = self.create_move_payment(customer_invoice_foreign, 15)
            self.assertEqual(payment3.state, "in_process")
            reconcile_move(customer_invoice_foreign, 30, 15)
            self.assertEqual(payment1.state, "paid")
            self.assertEqual(payment2.state, "in_process")
            self.assertEqual(payment3.state, "in_process")

            foreign_currency2 = self.other_currency
            customer_invoice_different_currencies = self.init_invoice(
                move_type="out_invoice", amounts=[100], post=True
            )
            payment1 = self.create_move_payment(
                customer_invoice_different_currencies, 5
            )
            self.assertEqual(payment1.state, "in_process")
            payment2 = self.create_move_payment(
                customer_invoice_different_currencies, 10
            )
            self.assertEqual(payment2.state, "in_process")
            payment3 = self.create_move_payment(
                customer_invoice_different_currencies, 20
            )
            self.assertEqual(payment3.state, "in_process")
            reconcile_move(
                customer_invoice_different_currencies, 10, currency=foreign_currency2
            )
            self.assertEqual(payment1.state, "paid")
            self.assertEqual(payment2.state, "in_process")
            self.assertEqual(payment3.state, "in_process")

            customer_invoice_outstanding = self.init_invoice(
                move_type="out_invoice", amounts=[300], post=True
            )
            payment1 = self.create_move_payment(customer_invoice_outstanding, 12, True)
            self.assertEqual(payment1.state, "in_process")
            payment2 = self.create_move_payment(customer_invoice_outstanding, 12)
            self.assertEqual(payment2.state, "in_process")
            reconcile_move(customer_invoice_outstanding, 12)
            reconcile_move(customer_invoice_outstanding, 12)
            self.assertEqual(payment1.state, "in_process")
            self.assertEqual(payment2.state, "paid")
            reconcile_move(
                payment1.move_id,
                12,
                lines_filter=lambda l: (
                    l.account_id.account_type
                    not in ("asset_receivable", "liability_payable")
                ),
            )
            self.assertEqual(payment1.state, "paid")

            customer_invoice_outstanding.line_ids.remove_move_reconcile()
            self.assertEqual(payment1.state, "paid")
            self.assertEqual(payment2.state, "in_process")
            payment1.move_id.line_ids.filtered(
                lambda l: (
                    l.account_id.account_type
                    not in ("asset_receivable", "liability_payable")
                )
            ).remove_move_reconcile()
            self.assertEqual(payment1.state, "in_process")

    def test_reconcile_partial_reconciliations(self):
        aml1 = self.create_line_for_reconciliation(
            1000.0, 1000.0, self.company_data["currency"], "2016-01-01"
        )
        aml2 = self.create_line_for_reconciliation(
            -999.0, -999.0, self.company_data["currency"], "2016-01-01"
        )
        aml3 = self.create_line_for_reconciliation(
            -1.0, -1.0, self.company_data["currency"], "2016-01-01"
        )

        (aml1 + aml2).reconcile()
        self.assertRecordValues(
            aml1 + aml2,
            [
                {"reconciled": False},
                {"reconciled": True},
            ],
        )
        self.assertTrue(aml1.matching_number.startswith("P"))
        self.assertEqual(aml1.matching_number, aml2.matching_number)

        with self.assertRaises(UserError):
            (aml2 + aml3).reconcile()

        (aml1 + aml2 + aml3).reconcile()
        self.assertRecordValues(
            aml1 + aml2 + aml3,
            [
                {"reconciled": True},
                {"reconciled": True},
                {"reconciled": True},
            ],
        )
        self.assertFalse(aml1.matching_number.startswith("P"))
        self.assertEqual(aml1.matching_number, aml3.matching_number)

    def test_caba_rounding_adjustment(self):
        self.env.company.account_config_id.tax_exigibility = True

        invoice = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": fields.Date.from_string("2016-01-01"),
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "caba test",
                            "quantity": 1,
                            "price_unit": 1000,
                            "tax_ids": [
                                Command.set(self.cash_basis_tax_tiny_amount_2.ids)
                            ],
                        }
                    )
                ],
            }
        )
        invoice.action_post()

        for amount in [100.1, 100.1, 100.1, 100.1, 400.2]:
            pmt_wizard = (
                self.env["account.payment.register"]
                .with_context(active_model="account.move", active_ids=invoice.ids)
                .create(
                    {
                        "amount": amount,
                    }
                )
            )
            pmt_wizard._create_payments()

        caba_moves = self.env["account.move"].search(
            [("tax_cash_basis_origin_move_id", "=", invoice.id)]
        )

        self.assertRecordValues(
            caba_moves.line_ids.sorted("id"),
            [
                {
                    "debit": 0.0,
                    "credit": 100.09,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 100.09,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[8].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[9].ids,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 100.09,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 100.09,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[8].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[9].ids,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 100.09,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 100.09,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[8].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[9].ids,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 100.09,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 100.09,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[8].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[9].ids,
                    "account_id": self.tax_account_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 400.18,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 400.18,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[8].ids,
                    "account_id": self.cash_basis_base_account.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.01,
                    "tax_tag_ids": [],
                    "account_id": self.cash_basis_transfer_account.id,
                },
                {
                    "debit": 0.01,
                    "credit": 0.0,
                    "tax_tag_ids": self.tax_tags[9].ids,
                    "account_id": self.tax_account_1.id,
                },
            ],
        )

    def test_modify_all_reconciled_lines(self):
        moves = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 1000.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 1000.0,
                                "credit": 0.0,
                                "account_id": self.company_data[
                                    "default_account_receivable"
                                ].id,
                            }
                        ),
                    ],
                },
                {
                    "move_type": "entry",
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 1000.0,
                                "account_id": self.company_data[
                                    "default_account_receivable"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 1000.0,
                                "credit": 0.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                    ],
                },
            ]
        )
        moves.action_post()
        receivable_lines = moves.line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_receivable"]
        )

        receivable_lines.reconcile()

        receivable_lines.account_id = self.company_data["default_account_payable"]
        self.assertEqual(receivable_lines.mapped("reconciled"), [True, True])

        with closing(self.env.cr.savepoint()):
            receivable_lines[0].account_id = self.company_data[
                "default_account_receivable"
            ]
            self.assertEqual(receivable_lines.mapped("reconciled"), [False, False])

        receivable_lines.partner_id = self.partner_a
        self.assertEqual(receivable_lines.mapped("reconciled"), [True, True])

        with closing(self.env.cr.savepoint()):
            receivable_lines.currency_id = self.other_currency
            self.assertEqual(receivable_lines.mapped("reconciled"), [False, False])

    def test_modify_all_reconciled_lines_with_no_partner(self):
        inv = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 1000.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 1000.0,
                                "credit": 0.0,
                                "account_id": self.company_data[
                                    "default_account_receivable"
                                ].id,
                            }
                        ),
                    ],
                }
            ]
        )

        bank_move = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 1000.0,
                                "credit": 0.0,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 1000.0,
                                "account_id": self.company_data[
                                    "default_account_receivable"
                                ].id,
                                "partner_id": self.partner_a.id,
                            }
                        ),
                    ],
                }
            ]
        )
        (inv + bank_move).action_post()
        rec_lines = (inv + bank_move).line_ids.filtered(
            lambda l: l.account_id == self.company_data["default_account_receivable"]
        )
        rec_lines.reconcile()

        self.assertEqual(rec_lines.mapped("reconciled"), [True, True])
        self.assertEqual(bank_move.partner_id.id, False)
        self.assertEqual(bank_move.commercial_partner_id.id, False)

        self.partner_a.parent_id = self.env["res.partner"].create(
            {"name": "new partner"}
        )
        self.assertEqual(rec_lines.mapped("reconciled"), [True, True])

    def test_links_between_move_and_payment(self):
        invoice_outstanding = self.init_invoice(
            move_type="out_invoice", amounts=[300], post=True
        )
        payment = self.create_move_payment(invoice_outstanding, 300, True)

        self.assertEqual(payment.reconciled_invoice_ids, invoice_outstanding)
        payment.action_draft()
        self.assertEqual(payment.reconciled_invoice_ids, invoice_outstanding)
        payment.action_post()
        self.assertEqual(payment.reconciled_invoice_ids, invoice_outstanding)

    def test_reconciliation_currency_exchange_matching_number(self):
        currency_chf = self.env.ref("base.CHF")

        account_receivable = self.company_data["default_account_receivable"]
        invoice_line = self.create_line_for_reconciliation(
            1000.0, 1000.0, currency_chf, "2025-01-01", account_receivable
        )
        payment_line = self.create_line_for_reconciliation(
            -500.0, -1000.0, currency_chf, "2025-02-01"
        )
        currency_exchange_line = self.create_line_for_reconciliation(
            -500.0, -0.0, currency_chf, "2025-02-01", account_receivable
        )

        lines = invoice_line + payment_line + currency_exchange_line
        lines.with_context(
            no_exchange_difference=True, no_exchange_difference_no_recursive=True
        ).reconcile()

        self.assertEqual(invoice_line.matching_number, payment_line.matching_number)
        self.assertEqual(
            payment_line.matching_number, currency_exchange_line.matching_number
        )
        self.assertEqual(currency_exchange_line.amount_residual, 0)

    def test_partial_reconcile_amounts_of_several_matching_lines(self):
        comp_curr = self.company_data["currency"]
        partner_c = self.partner_a.copy()
        line_1 = self.create_line_for_reconciliation(
            1000.0, 1000.0, comp_curr, "2016-01-01", partner=self.partner_a
        )
        line_2 = self.create_line_for_reconciliation(
            1001.0, 1001.0, comp_curr, "2016-01-01", partner=self.partner_b
        )
        line_3 = self.create_line_for_reconciliation(
            1002.0, 1002.0, comp_curr, "2016-01-01", partner=partner_c
        )
        line_4 = self.create_line_for_reconciliation(
            -1002.0, -1002.0, comp_curr, "2016-01-01", partner=partner_c
        )
        line_5 = self.create_line_for_reconciliation(
            -1001.0, -1001.0, comp_curr, "2016-01-01", partner=self.partner_b
        )
        line_6 = self.create_line_for_reconciliation(
            -1000.0, -1000.0, comp_curr, "2016-01-01", partner=self.partner_a
        )
        lines = line_1 + line_2 + line_3 + line_4 + line_5 + line_6
        lines.reconcile()
        reconciliation_lines = lines.full_reconcile_id.partial_reconcile_ids.sorted(
            "amount"
        )
        self.assertRecordValues(
            reconciliation_lines,
            [
                {
                    "amount": 1000.0,
                    "debit_move_id": line_1.id,
                    "credit_move_id": line_6.id,
                },
                {
                    "amount": 1001.0,
                    "debit_move_id": line_2.id,
                    "credit_move_id": line_5.id,
                },
                {
                    "amount": 1002.0,
                    "debit_move_id": line_3.id,
                    "credit_move_id": line_4.id,
                },
            ],
        )

    def test_exchange_move_assignment_with_group_payment(self):
        foreign_curr = self.setup_other_currency(
            "EUR",
            rates=[
                ("2025-01-01", 0.054493834023),
                ("2025-01-02", 0.054363189597),
            ],
        )

        inv1, inv2 = [
            self.init_invoice(
                "out_invoice",
                partner=self.partner_a,
                invoice_date="2025-01-01",
                post=True,
                products=[self.product_a],
                amounts=[amount],
                currency=foreign_curr,
            )
            for amount in [500.0, 10.0]
        ]

        payment = (
            self.env["account.payment.register"]
            .with_context(
                active_model="account.move",
                active_ids=(inv1 + inv2).ids,
            )
            .create(
                {
                    "payment_date": "2025-01-02",
                    "group_payment": True,
                    "amount": 510.0,
                    "currency_id": foreign_curr.id,
                }
            )
            ._create_payments()
        )

        partials = self.env["account.partial.reconcile"].search(
            [
                ("debit_move_id.move_id", "in", [inv1.id, inv2.id]),
                ("credit_move_id.move_id", "=", payment.move_id.id),
            ]
        )

        self.assertEqual(len(partials.mapped("exchange_move_id")), 2)

    def test_group_payment_state_updates_from_all_invoice_partials(self):
        invoices = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": "2025-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Grouped payment line",
                                "quantity": 1,
                                "price_unit": amount,
                            }
                        )
                    ],
                }
                for amount in (30.0, 10.0)
            ]
        )
        invoices.action_post()
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoices.ids)
            .create({"group_payment": True, "amount": 40.0})
            ._create_payments()
        )
        payment_lines = payment.move_id.line_ids
        partials = (
            payment_lines.matched_debit_ids | payment_lines.matched_credit_ids
        ).filtered(
            lambda partial: (
                partial.debit_move_id.move_id in invoices
                or partial.credit_move_id.move_id in invoices
            )
        )
        self.assertEqual(len(partials), 2)

        payment.outstanding_account_id = False
        payment.state = "paid"
        self.env.invalidate_all()
        with self.assertQueryCount(default=10, flush=False):
            result = partials._get_to_update_payments(from_state="paid")
        self.assertEqual(result, payment)

    def test_group_outbound_payment_state_updates_from_all_bill_partials(self):
        bills = self.env["account.move"].create(
            [
                {
                    "move_type": "in_invoice",
                    "partner_id": self.partner_a.id,
                    "invoice_date": "2025-01-01",
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "name": "Grouped bill line",
                                "quantity": 1,
                                "price_unit": amount,
                            }
                        )
                    ],
                }
                for amount in (30.0, 10.0)
            ]
        )
        bills.action_post()
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=bills.ids)
            .create({"group_payment": True, "amount": 40.0})
            ._create_payments()
        )
        payment_lines = payment.move_id.line_ids
        partials = payment_lines.matched_debit_ids | payment_lines.matched_credit_ids
        self.assertEqual(len(partials), 2)

        payment.outstanding_account_id = False
        payment.state = "paid"
        self.assertEqual(partials._get_to_update_payments(from_state="paid"), payment)

    def test_payment_state_updates_from_all_payment_term_partials(self):
        invoice = self.init_invoice(
            "out_invoice",
            partner=self.partner_a,
            invoice_date="2025-01-01",
            amounts=[100.0],
        )
        invoice.invoice_payment_term_id = self.pay_terms_b
        invoice.action_post()
        payment = (
            self.env["account.payment.register"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create({"amount": 100.0})
            ._create_payments()
        )
        payment_lines = payment.move_id.line_ids
        partials = payment_lines.matched_debit_ids | payment_lines.matched_credit_ids
        self.assertEqual(len(partials), 2)

        payment.outstanding_account_id = False
        payment.state = "paid"
        self.assertEqual(partials._get_to_update_payments(from_state="paid"), payment)

    def test_cash_basis_rejects_zero_allocation_total(self):
        currencies_and_errors = (
            (
                self.env.company.currency_id,
                "company-currency payment total is zero",
            ),
            (
                self.setup_other_currency(
                    "EUR", rates=[("2025-01-01", 1.0), ("2025-01-02", 1.0)]
                ),
                "foreign-currency payment total is zero",
            ),
        )
        for currency, error in currencies_and_errors:
            with self.subTest(currency=currency.name):
                debit_line = self.create_line_for_reconciliation(
                    100.0, 100.0, currency, "2025-01-01"
                )
                credit_line = self.create_line_for_reconciliation(
                    -100.0, -100.0, currency, "2025-01-02"
                )
                partial = self.env["account.partial.reconcile"].create(
                    {
                        "amount": 100.0,
                        "debit_amount_currency": 100.0,
                        "credit_amount_currency": 100.0,
                        "debit_move_id": debit_line.id,
                        "credit_move_id": credit_line.id,
                    }
                )
                move_values = {
                    "move": debit_line.move_id,
                    "to_process_lines": [("base", debit_line)],
                    "total_balance": 0.0,
                    "total_amount_currency": 0.0,
                    "currency": currency,
                }

                move_model = type(debit_line.move_id)
                with (
                    patch.object(
                        move_model,
                        "_collect_tax_cash_basis_values",
                        autospec=True,
                        side_effect=lambda move, move_values=move_values, debit_move=debit_line.move_id: (
                            move_values if move == debit_move else None
                        ),
                    ),
                    self.assertRaisesRegex(ValidationError, error),
                ):
                    partial._collect_tax_cash_basis_values()

    def test_cash_basis_keeps_product_tag_amounts_separate(self):
        self.env.company.account_config_id.tax_exigibility = True
        product_tags = self.env["account.account.tag"].create(
            [
                {"name": "CABA product A", "applicability": "products"},
                {"name": "CABA product B", "applicability": "products"},
            ]
        )
        products = self.env["product.product"].union(
            *(
                self._create_product(
                    account_tag_ids=[Command.set(tag.ids)],
                    taxes_id=self.cash_basis_tax_a_third_amount,
                )
                for tag in product_tags
            )
        )
        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "partner_id": self.partner_a.id,
                "invoice_date": "2025-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": product.id,
                            "quantity": 1,
                            "price_unit": amount,
                        }
                    )
                    for product, amount in zip(products, (100.0, 200.0), strict=True)
                ],
            }
        )
        invoice.action_post()
        self.assertEqual(
            invoice.invoice_line_ids.mapped("tax_tag_ids") & product_tags,
            product_tags,
        )
        self._register_payment(invoice, payment_date="2025-01-02")

        tagged_base_lines = invoice.tax_cash_basis_created_move_ids.line_ids.filtered(
            lambda line: line.tax_ids and line.tax_tag_ids & product_tags
        )
        self.assertEqual(
            {
                frozenset((line.tax_tag_ids & product_tags).ids): abs(
                    line.amount_currency
                )
                for line in tagged_base_lines
            },
            {
                frozenset(product_tags[0].ids): 100.0,
                frozenset(product_tags[1].ids): 200.0,
            },
        )

    def test_same_move_reconciliation_does_not_create_cash_basis_entry(self):
        self.env.company.account_config_id.tax_exigibility = True
        tax_repartition_line = (
            self.cash_basis_tax_a_third_amount.invoice_repartition_line_ids.filtered(
                lambda line: line.repartition_type == "tax"
            )
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2025-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": self.revenue_account.id,
                            "balance": -100.0,
                            "tax_ids": [
                                Command.set(self.cash_basis_tax_a_third_amount.ids)
                            ],
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.cash_basis_transfer_account.id,
                            "balance": -33.33,
                            "tax_repartition_line_id": tax_repartition_line.id,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.receivable_account.id,
                            "partner_id": self.partner_a.id,
                            "date_maturity": "2025-01-01",
                            "balance": 183.33,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.receivable_account.id,
                            "partner_id": self.partner_a.id,
                            "date_maturity": "2025-01-01",
                            "balance": -50.0,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        receivable_lines = move.line_ids.filtered(
            lambda line: line.account_id == self.receivable_account
        )
        receivable_lines.reconcile()

        self.assertFalse(move.tax_cash_basis_created_move_ids)

    def test_reconcile_cash_basis_payment_term_full_amount(self):
        self.env.company.account_config_id.tax_exigibility = True

        product = self._create_product(
            lst_price=100.0,
            taxes_id=self.cash_basis_tax_a_third_amount,
        )
        invoice = self._create_invoice_one_line(
            product_id=product,
            invoice_payment_term_id=self.pay_terms_b,
            post=True,
        )

        payments = self._register_payment(
            invoice,
            payment_date="2016-01-01",
            amount=invoice.amount_total,
            group_payment=False,
        )
        self.assertEqual(len(payments), 1)

        tax_cash_basis_moves = self._get_caba_moves(invoice)
        self.assertEqual(len(tax_cash_basis_moves), 2)
        self.assertRecordValues(
            tax_cash_basis_moves.line_ids.sorted(),
            [
                {"balance": 70.0},
                {"balance": -70.0},
                {"balance": 23.33},
                {"balance": -23.33},
                {"balance": 30.0},
                {"balance": -30.0},
                {"balance": 10.0},
                {"balance": -10.0},
            ],
        )

    def test_reconcile_cash_basis_payment_term_full_amount_two_invoices(self):
        self.env.company.account_config_id.tax_exigibility = True

        product = self._create_product(
            lst_price=100.0,
            taxes_id=self.cash_basis_tax_a_third_amount,
        )
        invoices = self._create_invoice_one_line(
            product_id=product,
            invoice_payment_term_id=self.pay_terms_b,
            post=True,
        ) | self._create_invoice_one_line(
            product_id=product,
            invoice_payment_term_id=self.pay_terms_b,
            post=True,
        )

        payments = self._register_payment(
            invoices,
            payment_date="2016-01-01",
            amount=sum(invoices.mapped("amount_total")),
            group_payment=False,
        )
        self.assertEqual(len(payments), 2)

        tax_cash_basis_moves = self._get_caba_moves(invoices)
        self.assertEqual(len(tax_cash_basis_moves), 4)
        self.assertRecordValues(
            tax_cash_basis_moves.line_ids.sorted(),
            [
                {"balance": 70.0},
                {"balance": -70.0},
                {"balance": 23.33},
                {"balance": -23.33},
                {"balance": 30.0},
                {"balance": -30.0},
                {"balance": 10.0},
                {"balance": -10.0},
                {"balance": 70.0},
                {"balance": -70.0},
                {"balance": 23.33},
                {"balance": -23.33},
                {"balance": 30.0},
                {"balance": -30.0},
                {"balance": 10.0},
                {"balance": -10.0},
            ],
        )
