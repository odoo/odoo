from odoo import Command
from odoo.tests import tagged

from .common_report_engine import TestAccountReportsCommon


@tagged("post_install", "-at_install")
class TestSpreadsheetAgreesWithTheAccountCodesEngine(TestAccountReportsCommon):
    """`spreadsheet_account` answers the same question as the `account_codes` engine.

    Two independent implementations of one accounting rule, and they resolve the date
    scope from different places: the spreadsheet per ACCOUNT, from
    `include_initial_balance`; the report per EXPRESSION, from `date_scope` read against
    the report's date filter mode. They agree on every shipped report measured on
    2026-09-09, and nothing but this file asserts that they keep agreeing.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.spreadsheet_installed = bool(
            cls.env["ir.module.module"].search(
                [("name", "=", "spreadsheet_account"), ("state", "=", "installed")]
            )
        )
        Account = cls.env["account.account"]
        cls.cumulative_account = Account.create(
            {
                "code": "970100",
                "name": "Agreement probe, balance sheet",
                "account_type": "liability_payable",
            }
        )
        cls.period_account = Account.create(
            {
                "code": "970200",
                "name": "Agreement probe, profit and loss",
                "account_type": "income",
            }
        )
        cls.counterpart = Account.create(
            {
                "code": "970900",
                "name": "Agreement probe, counterpart",
                "account_type": "asset_current",
            }
        )
        for account in (cls.cumulative_account, cls.period_account):
            cls._post_probe_move(account, "2019-06-15", 100.0)
            cls._post_probe_move(account, "2020-06-15", 10.0)

    @classmethod
    def _post_probe_move(cls, account, date, amount):
        move = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "date": date,
                "journal_id": cls.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {"account_id": account.id, "debit": amount, "credit": 0.0}
                    ),
                    Command.create(
                        {
                            "account_id": cls.counterpart.id,
                            "debit": 0.0,
                            "credit": amount,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def _assert_prefix_is_ours(self, prefix, expected):
        """A prefix that reaches a fixture account makes every assertion below a lie."""
        reached = self.env["account.account"].search([("code", "=like", f"{prefix}%")])
        self.assertEqual(
            reached,
            expected,
            f"prefix {prefix!r} no longer selects exactly the probe accounts",
        )

    def _spreadsheet_balance(self, prefix, year=2020):
        [result] = self.env["account.account"].spreadsheet_fetch_debit_credit(
            [
                {
                    "date_range": {"range_type": "year", "year": year},
                    "company_id": self.env.company.id,
                    "codes": [prefix],
                    "include_unposted": False,
                }
            ]
        )
        return result["debit"] - result["credit"]

    def _report_balance(self, prefix, *, date_range, date_scope="strict_range"):
        report = self.env["report.formula"].create(
            {
                "name": f"Agreement probe {prefix} {date_scope}",
                "filter_date_range": date_range,
                "column_ids": [
                    Command.create(
                        {
                            "name": "Balance",
                            "expression_label": "balance",
                            "sequence": 1,
                        }
                    )
                ],
                "line_ids": [
                    Command.create(
                        {
                            "name": f"Prefix {prefix}",
                            "code": f"PROBE{prefix}",
                            "account_codes_formula": prefix,
                        }
                    )
                ],
            }
        )
        report.line_ids.expression_ids.date_scope = date_scope
        options = report.get_options(
            {
                "selected_variant_id": report.id,
                "unfold_all": True,
                "date": {
                    "date_from": "2020-01-01",
                    "date_to": "2020-12-31",
                    "mode": "range" if date_range else "single",
                    "filter": "custom",
                },
            }
        )
        lines = report._get_lines(options)
        return lines[0]["columns"][0]["no_format"]

    def _skip_without_spreadsheet(self):
        if not self.spreadsheet_installed:
            self.skipTest(
                "spreadsheet_account is not installed, so the second implementation "
                "this file compares against is absent; install it to run these"
            )

    def test_an_as_of_report_over_cumulative_accounts_agrees_with_the_spreadsheet(self):
        self._skip_without_spreadsheet()
        self._assert_prefix_is_ours("9701", self.cumulative_account)
        self.assertEqual(
            self._report_balance("9701", date_range=False),
            self._spreadsheet_balance("9701"),
        )

    def test_a_range_report_over_period_accounts_agrees_with_the_spreadsheet(self):
        self._skip_without_spreadsheet()
        self._assert_prefix_is_ours("9702", self.period_account)
        self.assertEqual(
            self._report_balance("9702", date_range=True),
            self._spreadsheet_balance("9702"),
        )

    def test_a_range_report_over_cumulative_accounts_is_where_the_two_part_company(
        self,
    ):
        """The hazard, pinned so that closing it is a deliberate act.

        The spreadsheet reads a balance-sheet account cumulatively whatever range it is
        given; a range report reads the movement. Delete this test when the two stop
        resolving the scope from different places.
        """
        self._skip_without_spreadsheet()
        self._assert_prefix_is_ours("9701", self.cumulative_account)
        self.assertEqual(self._report_balance("9701", date_range=True), 10.0)
        self.assertEqual(self._spreadsheet_balance("9701"), 110.0)

    def test_a_prefix_spanning_both_kinds_is_reconcilable_by_no_date_scope(self):
        """No `date_scope` reproduces the spreadsheet across a mixed prefix.

        The spreadsheet mixes a cumulative and a period figure inside one sum, which a
        single expression cannot express. 44 shipped `account_codes` expressions carried
        such a prefix when this was written.
        """
        self._skip_without_spreadsheet()
        self._assert_prefix_is_ours(
            "970", self.cumulative_account + self.period_account + self.counterpart
        )
        spreadsheet = self._spreadsheet_balance("970")
        for date_scope in ("strict_range", "from_beginning"):
            with self.subTest(date_scope=date_scope):
                self.assertNotEqual(
                    self._report_balance("970", date_range=True, date_scope=date_scope),
                    spreadsheet,
                )
