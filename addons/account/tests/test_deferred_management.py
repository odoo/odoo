# pylint: disable=C0326
import datetime

from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestDeferredManagement(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_accounts = [
            cls.env["account.account"].create(
                {
                    "name": f"Expense {i}",
                    "code": f"EXP{i}",
                    "account_type": "expense",
                }
            )
            for i in range(3)
        ]
        cls.revenue_accounts = [
            cls.env["account.account"].create(
                {
                    "name": f"Revenue {i}",
                    "code": f"REV{i}",
                    "account_type": "income",
                }
            )
            for i in range(3)
        ]

        cls.company.account_config_id.deferred_expense_journal_id = cls.env[
            "account.journal"
        ].create(
            {
                "name": "Deferred Expense Journal",
                "code": "DEFEXP",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.company.account_config_id.deferred_revenue_journal_id = cls.env[
            "account.journal"
        ].create(
            {
                "name": "Deferred Revenue Journal",
                "code": "DEFREV",
                "type": "general",
                "company_id": cls.company.id,
            }
        )
        cls.company.account_config_id.deferred_expense_account_id = cls.company_data[
            "default_account_deferred_expense"
        ].id
        cls.company.account_config_id.deferred_revenue_account_id = cls.company_data[
            "default_account_deferred_revenue"
        ].id

        cls.expense_lines = [
            [
                cls.expense_accounts[0],
                1000,
                "2023-01-01",
                "2023-04-30",
            ],
            [
                cls.expense_accounts[0],
                1050,
                "2023-01-16",
                "2023-04-30",
            ],
            [
                cls.expense_accounts[1],
                1225,
                "2023-01-01",
                "2023-04-15",
            ],
            [
                cls.expense_accounts[2],
                1680,
                "2023-01-21",
                "2023-04-14",
            ],
            [
                cls.expense_accounts[2],
                225,
                "2023-04-01",
                "2023-04-15",
            ],
        ]
        cls.revenue_lines = [
            [
                cls.revenue_accounts[0],
                1000,
                "2023-01-01",
                "2023-04-30",
            ],
            [
                cls.revenue_accounts[0],
                1050,
                "2023-01-16",
                "2023-04-30",
            ],
            [
                cls.revenue_accounts[1],
                1225,
                "2023-01-01",
                "2023-04-15",
            ],
            [
                cls.revenue_accounts[2],
                1680,
                "2023-01-21",
                "2023-04-14",
            ],
            [
                cls.revenue_accounts[2],
                225,
                "2023-04-01",
                "2023-04-15",
            ],
        ]

    def create_invoice(self, move_type, move_lines, date=None, post=True):
        journal = self.company_data["default_journal_misc"]
        if move_type in self.env["account.move"].get_purchase_types():
            journal = self.company_data["default_journal_purchase"]
        elif move_type in self.env["account.move"].get_sale_types():
            journal = self.company_data["default_journal_sale"]
        move_vals = {
            "move_type": move_type,
            "partner_id": self.partner_a.id,
            "date": date or "2023-01-01",
            "invoice_date": date or "2023-01-01",
            "journal_id": journal.id,
        }
        if move_type != "entry":
            move_vals["invoice_line_ids"] = [
                Command.create(
                    {
                        "product_id": self.product_a.id,
                        "account_id": account.id,
                        "price_unit": balance,
                        "quantity": 1,
                        "deferred_start_date": start_date,
                        "deferred_end_date": end_date,
                    }
                )
                for account, balance, start_date, end_date in move_lines
            ]
        else:
            move_vals["line_ids"] = [
                Command.create(
                    {
                        "account_id": account.id,
                        "balance": balance,
                        "deferred_start_date": start_date,
                        "deferred_end_date": end_date,
                    }
                )
                for account, balance, start_date, end_date in move_lines
            ] + [
                Command.create(
                    {
                        "account_id": self.company_data[
                            "default_journal_bank"
                        ].default_account_id.id,
                        "balance": -sum(line[1] for line in move_lines),
                    }
                )
            ]
        move = self.env["account.move"].create(move_vals)
        if post:
            move.action_post()
        return move

    def test_deferred_management_get_diff_dates(self):
        def assert_get_diff_dates(start, end, expected):
            diff = self.env["account.move"]._get_deferred_diff_dates(
                fields.Date.to_date(start), fields.Date.to_date(end)
            )
            self.assertAlmostEqual(diff, expected, 3)

        assert_get_diff_dates("2023-01-01", "2023-01-01", 0)
        assert_get_diff_dates("2023-01-01", "2023-01-02", 1 / 30)
        assert_get_diff_dates("2023-01-01", "2023-01-20", 19 / 30)
        assert_get_diff_dates("2023-01-01", "2023-01-31", 29 / 30)
        assert_get_diff_dates("2023-01-01", "2023-01-30", 29 / 30)
        assert_get_diff_dates("2023-01-01", "2023-02-01", 1)
        assert_get_diff_dates("2023-01-01", "2023-02-28", 1 + 29 / 30)
        assert_get_diff_dates("2023-02-01", "2023-02-28", 29 / 30)
        assert_get_diff_dates("2023-02-10", "2023-02-28", 20 / 30)
        assert_get_diff_dates("2023-01-01", "2023-02-15", 1 + 14 / 30)
        assert_get_diff_dates("2023-01-01", "2023-03-31", 2 + 29 / 30)
        assert_get_diff_dates("2023-01-01", "2023-04-01", 3)
        assert_get_diff_dates("2023-01-01", "2023-04-30", 3 + 29 / 30)
        assert_get_diff_dates("2023-01-10", "2023-04-30", 3 + 20 / 30)
        assert_get_diff_dates("2023-01-10", "2023-04-09", 2 + 29 / 30)
        assert_get_diff_dates("2023-01-10", "2023-04-10", 3)
        assert_get_diff_dates("2023-01-10", "2023-04-11", 3 + 1 / 30)
        assert_get_diff_dates("2023-02-20", "2023-04-10", 1 + 20 / 30)
        assert_get_diff_dates("2023-01-31", "2023-04-30", 3)
        assert_get_diff_dates("2023-02-28", "2023-04-10", 1 + 10 / 30)
        assert_get_diff_dates("2023-03-01", "2023-04-10", 1 + 9 / 30)
        assert_get_diff_dates("2023-04-10", "2023-03-01", 1 + 9 / 30)
        assert_get_diff_dates("2023-01-01", "2023-12-31", 11 + 29 / 30)
        assert_get_diff_dates("2023-01-01", "2024-01-01", 12)
        assert_get_diff_dates("2023-01-01", "2024-07-01", 18)
        assert_get_diff_dates("2023-01-01", "2024-07-10", 18 + 9 / 30)

    def test_get_ends_of_month(self):
        def assertEndsOfMonths(start_date, end_date, expected):
            self.assertEqual(
                self.env["account.move.line"]._get_deferred_ends_of_month(
                    fields.Date.to_date(start_date), fields.Date.to_date(end_date)
                ),
                [fields.Date.to_date(date) for date in expected],
            )

        assertEndsOfMonths("2023-01-01", "2023-01-01", ["2023-01-31"])
        assertEndsOfMonths("2023-01-01", "2023-01-02", ["2023-01-31"])
        assertEndsOfMonths("2023-01-01", "2023-01-20", ["2023-01-31"])
        assertEndsOfMonths("2023-01-01", "2023-01-30", ["2023-01-31"])
        assertEndsOfMonths("2023-01-01", "2023-01-31", ["2023-01-31"])
        assertEndsOfMonths("2023-01-01", "2023-02-01", ["2023-01-31", "2023-02-28"])
        assertEndsOfMonths("2023-01-01", "2023-02-28", ["2023-01-31", "2023-02-28"])
        assertEndsOfMonths("2023-02-01", "2023-02-28", ["2023-02-28"])
        assertEndsOfMonths("2023-02-10", "2023-02-28", ["2023-02-28"])
        assertEndsOfMonths("2023-01-01", "2023-02-15", ["2023-01-31", "2023-02-28"])
        assertEndsOfMonths(
            "2023-01-01", "2023-03-31", ["2023-01-31", "2023-02-28", "2023-03-31"]
        )
        assertEndsOfMonths(
            "2023-01-01",
            "2023-04-01",
            ["2023-01-31", "2023-02-28", "2023-03-31", "2023-04-30"],
        )
        assertEndsOfMonths(
            "2023-01-01",
            "2023-04-30",
            ["2023-01-31", "2023-02-28", "2023-03-31", "2023-04-30"],
        )
        assertEndsOfMonths(
            "2023-01-10",
            "2023-04-30",
            ["2023-01-31", "2023-02-28", "2023-03-31", "2023-04-30"],
        )
        assertEndsOfMonths(
            "2023-01-10",
            "2023-04-09",
            ["2023-01-31", "2023-02-28", "2023-03-31", "2023-04-30"],
        )

    def test_deferred_abnormal_dates(self):
        move = self.create_invoice(
            "in_invoice",
            [
                [self.expense_accounts[0], 0, "2023-01-01", "2023-12-30"],
                [self.expense_accounts[0], 1, "2023-01-01", "2023-12-31"],
                [self.expense_accounts[0], 2, "2023-01-01", "2024-01-01"],
                [self.expense_accounts[0], 3, "2023-01-01", "2024-01-02"],
                [self.expense_accounts[0], 4, "2023-01-01", "2024-01-31"],
                [self.expense_accounts[0], 5, "2023-01-01", "2024-02-01"],
                [self.expense_accounts[0], 6, "2023-01-02", "2024-02-01"],
                [self.expense_accounts[0], 7, "2023-01-02", "2024-02-02"],
                [self.expense_accounts[0], 8, "2023-01-31", "2024-01-30"],
                [
                    self.expense_accounts[0],
                    9,
                    "2023-01-31",
                    "2024-02-28",
                ],
                [self.expense_accounts[0], 10, "2023-01-31", "2024-02-29"],
                [self.expense_accounts[0], 11, "2023-02-01", "2024-02-29"],
            ],
            post=True,
        )
        lines = move.invoice_line_ids.sorted("price_unit")
        self.assertFalse(lines[0].has_abnormal_deferred_dates)
        self.assertFalse(lines[1].has_abnormal_deferred_dates)
        self.assertTrue(lines[2].has_abnormal_deferred_dates)
        self.assertFalse(lines[3].has_abnormal_deferred_dates)
        self.assertFalse(lines[4].has_abnormal_deferred_dates)
        self.assertTrue(lines[5].has_abnormal_deferred_dates)
        self.assertFalse(lines[6].has_abnormal_deferred_dates)
        self.assertTrue(lines[7].has_abnormal_deferred_dates)
        self.assertFalse(lines[8].has_abnormal_deferred_dates)
        self.assertFalse(lines[9].has_abnormal_deferred_dates)
        self.assertTrue(lines[10].has_abnormal_deferred_dates)
        self.assertFalse(lines[11].has_abnormal_deferred_dates)

    def test_deferred_expense_generate_entries_method(self):
        self.company.account_config_id.generate_deferred_expense_entries_method = (
            "manual"
        )
        move = self.create_invoice("in_invoice", [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 0)

        move = self.create_invoice("in_refund", [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 0)

        self.company.account_config_id.generate_deferred_expense_entries_method = (
            "on_validation"
        )
        move = self.create_invoice("in_invoice", [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 5)

        move = self.create_invoice("in_refund", [self.expense_lines[0]], post=True)
        self.assertEqual(len(move.deferred_move_ids), 5)

    def test_deferred_expense_reset_to_draft(self):
        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 1680, "2023-01-21", "2023-04-14")],
            date="2023-03-15",
        )
        self.assertEqual(len(move.deferred_move_ids), 5)
        move.action_draft()
        self.assertFalse(move.deferred_move_ids)

        move.action_post()
        self.assertEqual(len(move.deferred_move_ids), 5)
        move.company_id.account_config_id.fiscalyear_lock_date = fields.Date.to_date(
            "2023-02-15"
        )
        move.action_draft()
        self.assertEqual(len(move.deferred_move_ids), 2)
        self.assertEqual(
            move.deferred_move_ids.sorted("date").mapped("date"),
            [fields.Date.to_date("2023-01-31"), fields.Date.to_date("2023-02-28")],
        )

        move.action_post()
        self.assertEqual(len(move.deferred_move_ids), 2 + 5)

    @freeze_time("2023-03-15")
    def test_deferred_invoice_reset_to_draft_with_audit_trail(self):
        invoice = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 1680, "2023-02-01", "2023-04-30")],
            date="2023-03-15",
        )
        posted_deferred_entries = invoice.deferred_move_ids.filtered(
            lambda move: move.state == "posted"
        )
        draft_deferred_move_ids = invoice.deferred_move_ids.filtered(
            lambda move: move.state == "draft"
        )
        self.assertEqual(len(posted_deferred_entries), 2)
        self.assertEqual(len(draft_deferred_move_ids), 2)

        self.env.company.account_config_id.restrictive_audit_trail = True
        invoice.action_draft()

        remaining_draft_moves = self.env["account.move"].search(
            [("id", "in", draft_deferred_move_ids.ids)]
        )
        self.assertFalse(remaining_draft_moves)
        self.assertEqual(
            len(posted_deferred_entries.filtered(lambda move: move.state == "cancel")),
            2,
        )

    def assert_invoice_lines(
        self, move, expected_values, source_account, deferred_account
    ):
        def source_balance(deferred_move):
            return sum(
                deferred_move.line_ids.filtered(
                    lambda line: line.account_id == source_account
                ).mapped("balance")
            )

        deferred_moves = move.deferred_move_ids.sorted(
            lambda deferred_move: (
                deferred_move.date,
                -abs(source_balance(deferred_move)),
            )
        )
        self.assertEqual(
            len(deferred_moves),
            len(expected_values),
            "every deferred entry must be accounted for by an expected row",
        )
        for deferred_move, expected_value in zip(
            deferred_moves, expected_values, strict=True
        ):
            (
                expected_date,
                expense_line_debit,
                expense_line_credit,
                deferred_line_debit,
                deferred_line_credit,
            ) = expected_value
            self.assertRecordValues(
                deferred_move,
                [
                    {
                        "state": "posted",
                        "move_type": "entry",
                        "partner_id": self.partner_a.id,
                        "date": fields.Date.to_date(expected_date),
                    }
                ],
            )
            expense_line = deferred_move.line_ids.filtered(
                lambda line: line.account_id == source_account
            )
            self.assertRecordValues(
                expense_line,
                [
                    {
                        "debit": expense_line_debit,
                        "credit": expense_line_credit,
                        "partner_id": self.partner_a.id,
                    },
                ],
            )
            deferred_line = deferred_move.line_ids.filtered(
                lambda line: line.account_id == deferred_account
            )
            self.assertEqual(deferred_line.debit, deferred_line_debit)
            self.assertEqual(deferred_line.credit, deferred_line_credit)

    def test_default_tax_on_account_not_on_deferred_entries(self):
        revenue_account_with_taxes = self.env["account.account"].create(
            {
                "name": "Revenue with Taxes",
                "code": "REVWTAXES",
                "account_type": "income",
                "tax_ids": [Command.set(self.tax_sale_a.ids)],
            }
        )

        move = self.create_invoice(
            "out_invoice",
            [[revenue_account_with_taxes, 1000, "2023-01-01", "2023-04-30"]],
            date="2022-12-10",
        )

        expected_line_values = [
            ("2022-12-10", 1000, 0, 0, 1000),
            ("2023-01-31", 0, 250, 250, 0),
            ("2023-02-28", 0, 250, 250, 0),
            ("2023-03-31", 0, 250, 250, 0),
            ("2023-04-30", 0, 250, 250, 0),
        ]

        self.assert_invoice_lines(
            move,
            expected_line_values,
            revenue_account_with_taxes,
            self.company_data["default_account_deferred_revenue"],
        )

        for deferred_move in move.deferred_move_ids:
            self.assertEqual(len(deferred_move.line_ids), 2)

    def test_deferred_values(self):
        expected_line_values1 = [
            ("2022-12-10", 0, 1000, 1000, 0),
            ("2023-01-31", 250, 0, 0, 250),
            ("2023-02-28", 250, 0, 0, 250),
            ("2023-03-31", 250, 0, 0, 250),
            ("2023-04-30", 250, 0, 0, 250),
        ]
        expected_line_values2 = [
            ("2022-12-10", 1000, 0, 0, 1000),
            ("2023-01-31", 0, 250, 250, 0),
            ("2023-02-28", 0, 250, 250, 0),
            ("2023-03-31", 0, 250, 250, 0),
            ("2023-04-30", 0, 250, 250, 0),
        ]

        def opening_on(date, expected_values):
            return [
                (fields.Date.to_date(date), *expected_values[0][1:]),
                *expected_values[1:],
            ]

        move = self.create_invoice(
            "in_invoice", [self.expense_lines[0]], post=True, date="2022-12-10"
        )
        self.assert_invoice_lines(
            move,
            expected_line_values1,
            self.expense_accounts[0],
            self.company_data["default_account_deferred_expense"],
        )
        reverse_move = move._reverse_moves([{"invoice_date": move.invoice_date}])
        reverse_move.action_post()
        self.assert_invoice_lines(
            reverse_move,
            opening_on("2022-12-31", expected_line_values2),
            self.expense_accounts[0],
            self.company_data["default_account_deferred_expense"],
        )

        move2 = self.create_invoice(
            "out_invoice", [self.revenue_lines[0]], post=True, date="2022-12-10"
        )
        self.assert_invoice_lines(
            move2,
            expected_line_values2,
            self.revenue_accounts[0],
            self.company_data["default_account_deferred_revenue"],
        )
        reverse_move2 = move2._reverse_moves([{"invoice_date": move2.invoice_date}])
        reverse_move2.action_post()
        self.assert_invoice_lines(
            reverse_move2,
            opening_on("2022-12-10", expected_line_values1),
            self.revenue_accounts[0],
            self.company_data["default_account_deferred_revenue"],
        )

    def test_deferred_values_rounding(self):
        expense_line = [self.expense_accounts[0], 500, "2020-08-07", "2020-12-07"]
        expected_line_values = [
            ("2020-08-07", 0, 500, 500, 0),
            ("2020-08-31", 99.17, 0, 0, 99.17),
            ("2020-09-30", 123.97, 0, 0, 123.97),
            ("2020-10-31", 123.97, 0, 0, 123.97),
            ("2020-11-30", 123.97, 0, 0, 123.97),
            ("2020-12-07", 28.92, 0, 0, 28.92),
        ]
        self.assertEqual(
            self.company.currency_id.round(sum(x[1] for x in expected_line_values)), 500
        )
        move = self.create_invoice("in_invoice", [expense_line], date="2020-08-07")
        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data["default_account_deferred_expense"],
        )

        revenue_line = [self.revenue_accounts[0], 500, "2020-08-07", "2020-12-07"]
        expected_line_values = [
            ("2020-08-07", 500, 0, 0, 500),
            ("2020-08-31", 0, 99.17, 99.17, 0),
            ("2020-09-30", 0, 123.97, 123.97, 0),
            ("2020-10-31", 0, 123.97, 123.97, 0),
            ("2020-11-30", 0, 123.97, 123.97, 0),
            ("2020-12-07", 0, 28.92, 28.92, 0),
        ]
        self.assertEqual(
            self.company.currency_id.round(sum(x[2] for x in expected_line_values)), 500
        )
        move = self.create_invoice(
            "out_invoice", [revenue_line], post=True, date="2020-08-07"
        )
        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.revenue_accounts[0],
            self.company_data["default_account_deferred_revenue"],
        )

    def test_deferred_expense_avoid_useless_deferred_entries(self):
        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 1680, "2023-01-01", "2023-01-31")],
            date="2023-01-01",
        )
        self.assertEqual(len(move.deferred_move_ids), 0)
        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 1680, "2023-01-01", "2023-01-31")],
            date="2022-01-01",
        )
        self.assertEqual(len(move.deferred_move_ids), 2)

    def test_deferred_expense_single_period_entries(self):
        self.company.account_config_id.deferred_expense_amount_computation_method = (
            "month"
        )
        move = self.create_invoice(
            "in_invoice", [(self.expense_accounts[0], 1680, "2023-02-01", "2023-02-28")]
        )
        self.assertRecordValues(
            move.deferred_move_ids,
            [
                {"date": fields.Date.to_date("2023-01-01")},
                {"date": fields.Date.to_date("2023-02-28")},
            ],
        )

    def test_taxes_deferred_after_date_added(self):
        expected_line_values = [
            ("2022-12-10", 0, 1000, 1000, 0),
            ("2022-12-10", 0, 100, 100, 0),
            ("2023-01-31", 250, 0, 0, 250),
            ("2023-01-31", 25, 0, 0, 25),
            ("2023-02-28", 250, 0, 0, 250),
            ("2023-02-28", 25, 0, 0, 25),
            ("2023-03-31", 250, 0, 0, 250),
            ("2023-03-31", 25, 0, 0, 25),
            ("2023-04-30", 250, 0, 0, 250),
            ("2023-04-30", 25, 0, 0, 25),
        ]

        partially_deductible_tax = self.env["account.tax"].create(
            {
                "name": "Partially deductible Tax",
                "amount": 20,
                "amount_type": "percent",
                "type_tax_use": "purchase",
                "invoice_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "account_id": self.company_data[
                                "default_account_tax_purchase"
                            ].id,
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
                "refund_repartition_line_ids": [
                    Command.create({"repartition_type": "base"}),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "use_in_tax_closing": False,
                        }
                    ),
                    Command.create(
                        {
                            "factor_percent": 50,
                            "repartition_type": "tax",
                            "account_id": self.company_data[
                                "default_account_tax_purchase"
                            ].id,
                            "use_in_tax_closing": True,
                        }
                    ),
                ],
            }
        )

        move = self.env["account.move"].create(
            {
                "move_type": "in_invoice",
                "partner_id": self.partner_a.id,
                "date": "2022-12-10",
                "invoice_date": "2022-12-10",
                "journal_id": self.company_data["default_journal_purchase"].id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "quantity": 1,
                            "account_id": self.expense_lines[0][0].id,
                            "price_unit": self.expense_lines[0][1],
                            "tax_ids": [Command.set(partially_deductible_tax.ids)],
                        }
                    )
                ],
            }
        )

        move.invoice_line_ids.write(
            {
                "deferred_start_date": self.expense_lines[0][2],
                "deferred_end_date": self.expense_lines[0][3],
            }
        )

        move.action_post()

        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data["default_account_deferred_expense"],
        )

    def test_deferred_tax_key(self):
        lines = [
            [self.expense_accounts[0], 1000, "2023-01-01", "2023-04-30"],
            [self.expense_accounts[0], 1000, False, False],
        ]
        move = self.create_invoice("in_invoice", lines, post=True)
        original_amount_total = move.amount_total
        self.assertEqual(
            len(move.line_ids.filtered(lambda l: l.display_type == "tax")), 1
        )
        move.action_draft()
        move.action_post()
        self.assertEqual(
            len(move.line_ids.filtered(lambda l: l.display_type == "tax")), 1
        )
        self.assertEqual(move.amount_total, original_amount_total)

    def test_compute_empty_start_date(self):
        lines = [[self.expense_accounts[0], 1000, False, "2023-04-30"]]
        move = self.create_invoice("in_invoice", lines, post=False)

        self.assertFalse(move.line_ids[0].deferred_start_date)

        move.action_post()
        self.assertEqual(
            move.line_ids[0].deferred_start_date, datetime.date(2023, 1, 1)
        )

        move.action_draft()
        move.line_ids[0].deferred_start_date = False
        move.invoice_date = "2023-02-01"
        self.assertEqual(
            move.line_ids[0].deferred_start_date, datetime.date(2023, 2, 1)
        )

        move.line_ids[0].deferred_start_date = False
        move.line_ids[0].deferred_end_date = "2023-05-31"
        self.assertEqual(
            move.line_ids[0].deferred_start_date, datetime.date(2023, 2, 1)
        )

    def test_deferred_on_accounting_date(self):
        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 1680, "2023-01-01", "2023-02-28")],
            date="2023-01-10",
            post=False,
        )
        move.date = "2023-01-15"
        move.action_post()
        self.assertRecordValues(
            move.deferred_move_ids,
            [
                {"date": fields.Date.to_date("2023-01-15")},
                {"date": fields.Date.to_date("2023-01-31")},
                {"date": fields.Date.to_date("2023-02-28")},
            ],
        )

    def test_deferred_entries_not_created_on_future_invoice(self):
        tomorrow = fields.Date.to_date(fields.Date.today()) + datetime.timedelta(days=1)
        move = self.create_invoice(
            "out_invoice",
            [
                (
                    self.expense_accounts[0],
                    1680,
                    tomorrow,
                    tomorrow + datetime.timedelta(days=100),
                )
            ],
            date=tomorrow,
            post=False,
        )
        move.auto_post = "at_date"
        move._post()
        self.assertFalse(move.deferred_move_ids)

        with freeze_time(tomorrow), self.enter_registry_test_mode():
            self.env.ref(
                "account.ir_cron_auto_post_draft_entry"
            ).method_direct_trigger()
            self.assertEqual(move.state, "posted")
            self.assertTrue(move.deferred_move_ids)

    def test_deferred_entries_created_on_auto_post_invoice(self):
        yesterday = fields.Date.to_date(fields.Date.today()) - datetime.timedelta(
            days=1
        )
        move = self.create_invoice(
            "out_invoice",
            [
                (
                    self.expense_accounts[0],
                    1680,
                    yesterday,
                    yesterday + datetime.timedelta(days=45),
                )
            ],
            date=yesterday,
            post=False,
        )
        move.auto_post = "at_date"
        move._post()
        self.assertEqual(move.state, "posted")
        self.assertTrue(move.deferred_move_ids)

    def test_deferred_compute_method_full_months(self):
        self.company.account_config_id.deferred_expense_amount_computation_method = (
            "full_months"
        )

        dates = (("2024-06-05", "2025-06-04"), ("2024-06-30", "2025-06-29"))
        for date_from, date_to in dates:
            move = self.create_invoice(
                "in_invoice",
                [(self.expense_accounts[0], 12000, date_from, date_to)],
                date="2024-06-05",
            )
            self.assertRecordValues(
                move.deferred_move_ids.sorted("date"),
                [
                    {"date": fields.Date.to_date("2024-06-05"), "amount_total": 12000},
                    {"date": fields.Date.to_date("2024-06-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-07-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-08-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-09-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-10-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-11-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-12-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-01-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-02-28"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-03-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-04-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-05-31"), "amount_total": 1000},
                ],
            )

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-07-01", "2025-06-30")],
            date="2024-07-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-07-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-07-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-08-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-09-30"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-10-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-11-30"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-12-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-01-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-02-28"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-03-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-04-30"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-05-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-06-30"), "amount_total": 1000},
            ],
        )

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-01", "2024-01-16")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-01", "2024-02-29")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 6000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 6000},
            ],
        )

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-15", "2024-03-14")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 6000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 6000},
            ],
        )

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-15", "2024-02-14")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-01", "2024-02-15")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-05", "2024-02-15")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-02-15", "2024-03-14")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 12000},
            ],
        )

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-02-05", "2024-03-15")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 12000},
            ],
        )

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-16", "2024-02-29")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 6000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 6000},
            ],
        )

        move = self.create_invoice(
            "in_invoice",
            [(self.expense_accounts[0], 12000, "2024-01-16", "2024-03-31")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 4000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 4000},
                {"date": fields.Date.to_date("2024-03-31"), "amount_total": 4000},
            ],
        )

    def test_deferred_compute_method_full_months_revenue(self):
        self.company.account_config_id.deferred_revenue_amount_computation_method = (
            "full_months"
        )

        dates = (("2024-06-05", "2025-06-04"), ("2024-06-30", "2025-06-29"))
        for date_from, date_to in dates:
            move = self.create_invoice(
                "out_invoice",
                [(self.revenue_accounts[0], 12000, date_from, date_to)],
                date="2024-06-05",
            )
            self.assertRecordValues(
                move.deferred_move_ids.sorted("date"),
                [
                    {"date": fields.Date.to_date("2024-06-05"), "amount_total": 12000},
                    {"date": fields.Date.to_date("2024-06-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-07-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-08-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-09-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-10-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-11-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2024-12-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-01-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-02-28"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-03-31"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-04-30"), "amount_total": 1000},
                    {"date": fields.Date.to_date("2025-05-31"), "amount_total": 1000},
                ],
            )

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-07-01", "2025-06-30")],
            date="2024-07-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-07-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-07-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-08-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-09-30"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-10-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-11-30"), "amount_total": 1000},
                {"date": fields.Date.to_date("2024-12-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-01-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-02-28"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-03-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-04-30"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-05-31"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-06-30"), "amount_total": 1000},
            ],
        )

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-01", "2024-01-16")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-01", "2024-02-29")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 6000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 6000},
            ],
        )

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-15", "2024-03-14")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 6000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 6000},
            ],
        )

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-15", "2024-02-14")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-01", "2024-02-15")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-05", "2024-02-15")],
            date="2024-01-01",
        )
        self.assertFalse(move.deferred_move_ids)

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-02-15", "2024-03-14")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 12000},
            ],
        )

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-02-05", "2024-03-15")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 12000},
            ],
        )

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-16", "2024-02-29")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 6000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 6000},
            ],
        )

        move = self.create_invoice(
            "out_invoice",
            [(self.revenue_accounts[0], 12000, "2024-01-16", "2024-03-31")],
            date="2024-01-01",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted(lambda m: (m.date, m.amount_total)),
            [
                {"date": fields.Date.to_date("2024-01-01"), "amount_total": 12000},
                {"date": fields.Date.to_date("2024-01-31"), "amount_total": 4000},
                {"date": fields.Date.to_date("2024-02-29"), "amount_total": 4000},
                {"date": fields.Date.to_date("2024-03-31"), "amount_total": 4000},
            ],
        )

    def test_deferral_moves_not_removed(self):
        move = self.create_invoice(
            "in_invoice",
            [
                (self.expense_accounts[0], 1000, "2025-05-10", "2025-05-25"),
                (self.expense_accounts[0], 1000, "2025-05-10", "2025-05-25"),
            ],
            date="2025-04-11",
        )
        self.assertEqual(len(move.deferred_move_ids), 4)

    def test_case_1_deferred_entries_computations_period_across_months(self):
        invoice_date = "2024-07-01"
        invoice_line_data = [self.expense_accounts[0], 1300, "2024-06-25", "2024-07-07"]

        expected_line_values = [
            ("2024-06-30", 600, 0, 0, 600),
            (invoice_date, 0, 1300, 1300, 0),
            ("2024-07-07", 700, 0, 0, 700),
        ]

        move = self.create_invoice("in_invoice", [invoice_line_data], date=invoice_date)

        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data["default_account_deferred_expense"],
        )

    def test_case_2_deferred_entries_computations_period_across_months(self):
        invoice_date = "2024-06-29"
        invoice_line_data = [self.expense_accounts[0], 1300, "2024-06-25", "2024-07-07"]

        expected_line_values = [
            (invoice_date, 0, 1300, 1300, 0),
            ("2024-06-30", 600, 0, 0, 600),
            ("2024-07-07", 700, 0, 0, 700),
        ]

        move = self.create_invoice("in_invoice", [invoice_line_data], date=invoice_date)

        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data["default_account_deferred_expense"],
        )

    def test_case_3_deferred_entries_computations_period_across_months(self):
        invoice_date = "2024-06-29"
        invoice_line_data = [self.expense_accounts[0], 2900, "2024-06-25", "2024-07-23"]

        expected_line_values = [
            (invoice_date, 0, 2900, 2900, 0),
            ("2024-06-30", 600, 0, 0, 600),
            ("2024-07-23", 2300, 0, 0, 2300),
        ]

        move = self.create_invoice("in_invoice", [invoice_line_data], date=invoice_date)

        self.assert_invoice_lines(
            move,
            expected_line_values,
            self.expense_accounts[0],
            self.company_data["default_account_deferred_expense"],
        )

    def test_deferred_moves_from_same_move_different_lines(self):
        move = self.create_invoice(
            "in_invoice",
            [
                (self.expense_accounts[0], amount, "2025-10-01", "2025-11-30")
                for amount in (1000, 500)
            ],
            date="2025-11-30",
        )
        self.assertRecordValues(
            move.deferred_move_ids.sorted("date"),
            [
                {"date": fields.Date.to_date("2025-10-31"), "amount_total": 500},
                {"date": fields.Date.to_date("2025-10-31"), "amount_total": 250},
                {"date": fields.Date.to_date("2025-11-30"), "amount_total": 1000},
                {"date": fields.Date.to_date("2025-11-30"), "amount_total": 500},
                {"date": fields.Date.to_date("2025-11-30"), "amount_total": 500},
                {"date": fields.Date.to_date("2025-11-30"), "amount_total": 250},
            ],
        )

    def test_deferred_misc(self):
        deferred_move = self.create_invoice(
            "entry",
            [
                (self.revenue_accounts[0], 30, "2025-01-01", "2025-03-31"),
                (self.expense_accounts[0], 300, "2025-01-01", "2025-03-31"),
            ],
            date="2025-01-01",
        )
        deferral_moves = deferred_move.deferred_move_ids.sorted(
            lambda m: (m.date, m.amount_total)
        )
        self.assertEqual(len(deferral_moves), 8)

        self.assertRecordValues(
            deferral_moves[:2].line_ids.sorted("balance"),
            [
                {
                    "date": fields.Date.to_date("2025-01-01"),
                    "balance": -300,
                    "account_id": self.expense_accounts[0].id,
                    "journal_id": self.company.account_config_id.deferred_expense_journal_id.id,
                },
                {
                    "date": fields.Date.to_date("2025-01-01"),
                    "balance": -30,
                    "account_id": self.revenue_accounts[0].id,
                    "journal_id": self.company.account_config_id.deferred_revenue_journal_id.id,
                },
                {
                    "date": fields.Date.to_date("2025-01-01"),
                    "balance": 30,
                    "account_id": self.company.account_config_id.deferred_revenue_account_id.id,
                    "journal_id": self.company.account_config_id.deferred_revenue_journal_id.id,
                },
                {
                    "date": fields.Date.to_date("2025-01-01"),
                    "balance": 300,
                    "account_id": self.company.account_config_id.deferred_expense_account_id.id,
                    "journal_id": self.company.account_config_id.deferred_expense_journal_id.id,
                },
            ],
        )
        for i, date in enumerate(["2025-01-31", "2025-02-28", "2025-03-31"]):
            self.assertRecordValues(
                deferral_moves[2 + 2 * i : 2 + 2 * (i + 1)].line_ids.sorted("balance"),
                [
                    {
                        "date": fields.Date.to_date(date),
                        "balance": -100,
                        "account_id": self.company.account_config_id.deferred_expense_account_id.id,
                        "journal_id": self.company.account_config_id.deferred_expense_journal_id.id,
                    },
                    {
                        "date": fields.Date.to_date(date),
                        "balance": -10,
                        "account_id": self.company.account_config_id.deferred_revenue_account_id.id,
                        "journal_id": self.company.account_config_id.deferred_revenue_journal_id.id,
                    },
                    {
                        "date": fields.Date.to_date(date),
                        "balance": 10,
                        "account_id": self.revenue_accounts[0].id,
                        "journal_id": self.company.account_config_id.deferred_revenue_journal_id.id,
                    },
                    {
                        "date": fields.Date.to_date(date),
                        "balance": 100,
                        "account_id": self.expense_accounts[0].id,
                        "journal_id": self.company.account_config_id.deferred_expense_journal_id.id,
                    },
                ],
            )

    def test_deferred_misc_diff_accounts_diff_methods(self):
        self.company.account_config_id.generate_deferred_expense_entries_method = (
            "on_validation"
        )
        self.company.account_config_id.generate_deferred_revenue_entries_method = (
            "manual"
        )
        deferred_move = self.create_invoice(
            "entry",
            [
                (self.revenue_accounts[0], 30, "2025-01-01", "2025-03-31"),
                (self.expense_accounts[0], 300, "2025-01-01", "2025-03-31"),
            ],
            date="2025-01-01",
            post=False,
        )
        with self.assertRaisesRegex(
            UserError,
            r"Having different deferred entries generation methods for expenses and revenues is not supported...",
        ):
            deferred_move.action_post()

    def test_misc_entry_no_deferred_dates_with_diff_methods(self):
        self.company.account_config_id.generate_deferred_expense_entries_method = (
            "on_validation"
        )
        self.company.account_config_id.generate_deferred_revenue_entries_method = (
            "manual"
        )
        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2025-01-01",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {"account_id": self.expense_accounts[0].id, "balance": 100}
                    ),
                    Command.create(
                        {"account_id": self.revenue_accounts[0].id, "balance": -100}
                    ),
                ],
            }
        )
        move.action_post()
        self.assertEqual(move.state, "posted")

    def test_deferred_move_lines_partner(self):
        invoice = self._create_invoice(
            invoice_date="2026-04-15",
            partner_id=self.partner_a,
            partner_shipping_id=self.partner_b,
            invoice_line_ids=[
                self._prepare_invoice_line(
                    price_unit=1000,
                    deferred_start_date="2026-03-01",
                    deferred_end_date="2026-04-30",
                )
            ],
        )
        invoice.with_context(default_partner_id=self.partner_b).action_post()
        self.assertEqual(
            invoice.deferred_move_ids.line_ids.mapped("partner_id"), self.partner_a
        )
