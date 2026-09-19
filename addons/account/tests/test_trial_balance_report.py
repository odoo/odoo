# pylint: disable=C0326
from odoo import Command, fields
from odoo.tests import tagged

from .common_report_engine import TestAccountReportsCommon


@tagged("post_install", "-at_install")
class TestTrialBalanceReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Give codes in company_1 to the accounts in company_2.
        context = {
            "allowed_company_ids": [
                cls.company_data["company"].id,
                cls.company_data_2["company"].id,
            ]
        }
        cls.company_data_2["default_account_payable"].with_context(
            context
        ).code = "211010"
        cls.company_data_2["default_account_revenue"].with_context(
            context
        ).code = "400010"
        cls.company_data_2["default_account_expense"].with_context(
            context
        ).code = "600010"

        # Entries in 2016 for company_1 to test the initial balance.
        cls.move_2016_1 = cls.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2016-01-01"),
                    "journal_id": cls.company_data["default_journal_misc"].id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "2016_1_1",
                                "account_id": cls.company_data[
                                    "default_account_payable"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 200.0,
                                "credit": 0.0,
                                "name": "2016_1_2",
                                "account_id": cls.company_data[
                                    "default_account_expense"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 300.0,
                                "name": "2016_1_3",
                                "account_id": cls.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                    ],
                }
            ]
        )
        cls.move_2016_1.action_post()

        # Entries in 2016 for company_2 to test the initial balance in multi-companies/multi-currencies.
        cls.move_2016_2 = cls.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2016-06-01"),
                    "journal_id": cls.company_data_2["default_journal_misc"].id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "2016_2_1",
                                "account_id": cls.company_data_2[
                                    "default_account_payable"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "name": "2016_2_2",
                                "account_id": cls.company_data_2[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                    ],
                }
            ]
        )
        cls.move_2016_2.action_post()

        # Entry in 2017 for company_1 to test the report at current date.
        cls.move_2017_1 = cls.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2017-01-01"),
                    "journal_id": cls.company_data["default_journal_sale"].id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 1000.0,
                                "credit": 0.0,
                                "name": "2017_1_1",
                                "account_id": cls.company_data[
                                    "default_account_receivable"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 2000.0,
                                "credit": 0.0,
                                "name": "2017_1_2",
                                "account_id": cls.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 3000.0,
                                "credit": 0.0,
                                "name": "2017_1_3",
                                "account_id": cls.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 4000.0,
                                "credit": 0.0,
                                "name": "2017_1_4",
                                "account_id": cls.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 5000.0,
                                "credit": 0.0,
                                "name": "2017_1_5",
                                "account_id": cls.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 6000.0,
                                "credit": 0.0,
                                "name": "2017_1_6",
                                "account_id": cls.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 6000.0,
                                "name": "2017_1_7",
                                "account_id": cls.company_data[
                                    "default_account_expense"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 7000.0,
                                "name": "2017_1_8",
                                "account_id": cls.company_data[
                                    "default_account_expense"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 8000.0,
                                "name": "2017_1_9",
                                "account_id": cls.company_data[
                                    "default_account_expense"
                                ].id,
                            },
                        ),
                    ],
                }
            ]
        )
        cls.move_2017_1.action_post()

        # Entry in 2017 for company_2 to test the current period in multi-companies/multi-currencies.
        cls.move_2017_2 = cls.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2017-06-01"),
                    "journal_id": cls.company_data_2["default_journal_bank"].id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 400.0,
                                "credit": 0.0,
                                "name": "2017_2_1",
                                "account_id": cls.company_data_2[
                                    "default_account_expense"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 400.0,
                                "name": "2017_2_2",
                                "account_id": cls.company_data_2[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                    ],
                }
            ]
        )
        cls.move_2017_2.action_post()

        # Archive 'default_journal_bank' to ensure archived entries are not filtered out.
        cls.company_data_2["default_journal_bank"].active = False

        # Deactivate all currencies to ensure group_multi_currency is disabled.
        cls.env["res.currency"].search([("name", "!=", "USD")]).with_context(
            force_deactivate=True
        ).active = False

        cls.report = cls.env.ref("account.trial_balance_report")
        cls.company_data["company"].account_config_id.totals_below_sections = False

    # -------------------------------------------------------------------------
    # Helper functions
    # -------------------------------------------------------------------------
    def _create_invoice_move(self, date, partner_id=False):
        return self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string(date),
                    "journal_id": self.company_data["default_journal_misc"].id,
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 1000.0,
                                "credit": 0.0,
                                "name": "payable",
                                "account_id": self.company_data[
                                    "default_account_payable"
                                ].id,
                                "partner_id": partner_id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 2000.0,
                                "credit": 0.0,
                                "name": "expense",
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 3000.0,
                                "name": "revenue",
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                    ],
                }
            ]
        )

    # -------------------------------------------------------------------------
    # TESTS: Trial Balance
    # -------------------------------------------------------------------------
    def test_trial_balance_unaffected_earnings_current_fiscal_year(self):
        move_2009_12 = self._create_invoice_move("2009-12-31")
        move_2009_12.action_post()

        move_2010_01 = self._create_invoice_move("2010-01-31")
        move_2010_01.action_post()

        move_2010_02 = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2010-02-01"),
                    "journal_id": self.company_data["default_journal_misc"].id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "payable",
                                "account_id": self.company_data[
                                    "default_account_payable"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 200.0,
                                "credit": 0.0,
                                "name": "expense",
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 300.0,
                                "name": "revenue",
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                    ],
                }
            ]
        )
        move_2010_02.action_post()

        move_2010_03 = self._create_invoice_move("2010-03-01")
        move_2010_03.action_post()

        options = self._generate_options(
            self.report,
            fields.Date.from_string("2010-02-01"),
            fields.Date.from_string("2010-02-28"),
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #   Name                                         Initial Balance         Debit          Credit          End Balance
            [0, 1, 2, 3, 4],
            [
                ("211000 Account Payable", 2000.0, 100.0, 0.0, 2100.0),
                ("400000 Product Sales", -3000.0, 0.0, 300.0, -3300.0),
                ("600000 Expenses", 2000.0, 200.0, 0.0, 2200.0),
                ("Result Brought Forward - company_1_data", -1000.0, 0.0, 0.0, -1000.0),
                ("Total", 0.0, 300.0, 300.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_unaffected_earnings_previous_fiscal_year(self):
        move_2009_12 = self._create_invoice_move("2009-12-31")
        move_2009_12.action_post()

        move_2010_01 = self._create_invoice_move("2010-01-31")
        move_2010_01.action_post()

        move_2010_02 = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2010-02-01"),
                    "journal_id": self.company_data["default_journal_misc"].id,
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "payable",
                                "account_id": self.company_data[
                                    "default_account_payable"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 200.0,
                                "credit": 0.0,
                                "name": "expense",
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "debit": 0.0,
                                "credit": 300.0,
                                "name": "revenue",
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            },
                        ),
                    ],
                }
            ]
        )
        move_2010_02.action_post()

        move_2010_03 = self._create_invoice_move("2010-03-01")
        move_2010_03.action_post()

        options = self._generate_options(
            self.report,
            fields.Date.from_string("2010-01-01"),
            fields.Date.from_string("2010-02-28"),
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                                        Initial Balance         Debit          Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("211000 Account Payable", 1000.0, 1100.0, 0.0, 2100.0),
                ("400000 Product Sales", 0.0, 0.0, 3300.0, -3300.0),
                ("600000 Expenses", 0.0, 2200.0, 0.0, 2200.0),
                ("Result Brought Forward - company_1_data", -1000.0, 0.0, 0.0, -1000.0),
                ("Total", 0.0, 3300.0, 3300.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_whole_report(self):
        options = self._generate_options(
            self.report,
            fields.Date.from_string("2017-01-01"),
            fields.Date.from_string("2017-12-31"),
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                                     Initial Balance          Debit         Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("121000 Account Receivable", 0.0, 1000.0, 0.0, 1000.0),
                ("211000 Account Payable", 100.0, 0.0, 0.0, 100.0),
                ("211010 Account Payable", 50.0, 0.0, 0.0, 50.0),
                ("400000 Product Sales", 0.0, 20000.0, 0.0, 20000.0),
                ("400010 Product Sales", 0.0, 0.0, 200.0, -200.0),
                ("600000 Expenses", 0.0, 0.0, 21000.0, -21000.0),
                ("600010 Expenses", 0.0, 200.0, 0.0, 200.0),
                ("Result Brought Forward - company_1_data", -100.0, 0.0, 0.0, -100.0),
                ("Result Brought Forward - company_2", -50.0, 0.0, 0.0, -50.0),
                ("Total", 0.0, 21200.0, 21200.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_filter_journals(self):
        self.env = self.env(
            context=dict(self.env.context, allowed_company_ids=self.env.company.ids)
        )
        self.report = self.report.with_env(self.env)

        options = self._generate_options(
            self.report,
            fields.Date.from_string("2017-01-01"),
            fields.Date.from_string("2017-12-31"),
        )
        options = self._update_multi_selector_filter(
            options, "journals", self.company_data["default_journal_sale"].ids
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                            Initial Balance         Debit          Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("121000 Account Receivable", 0.0, 1000.0, 0.0, 1000.0),
                ("400000 Product Sales", 0.0, 20000.0, 0.0, 20000.0),
                ("600000 Expenses", 0.0, 0.0, 21000.0, -21000.0),
                ("Total", 0.0, 21000.0, 21000.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_comparisons(self):
        # Ensure the comparison filter between years + ascending/descending option
        options = self._generate_options(self.report, "2017-01-01", "2017-12-31")
        options = self._update_comparison_filter(
            options,
            self.report,
            "previous_period",
            1,
            fields.Date.from_string("2017-01-01"),
            fields.Date.from_string("2017-12-31"),
        )
        expected_header_values = [
            {
                "name": "Initial Balance",
                "forced_options": {
                    "date": {
                        "string": "As of 12/31/2015",
                        "period_type": "custom",
                        "currency_table_period_key": "_trial_balance_middle_periods",
                        "mode": "single",
                        "date_from": False,
                        "date_to": "2015-12-31",
                    },
                    "trial_balance_column_block_id": "0",
                    "trial_balance_column_type": "initial_balance",
                    "trial_balance_block_fiscalyear_start": "2016-01-01",
                },
                "colspan": 1,
            },
            {
                "name": "2016",
                "forced_options": {
                    "date": {
                        "string": "2016",
                        "period_type": "fiscalyear",
                        "currency_table_period_key": "_trial_balance_middle_periods",
                        "mode": "range",
                        "date_from": "2016-01-01",
                        "date_to": "2016-12-31",
                    },
                },
            },
            {
                "name": "End Balance",
                "forced_options": {
                    "date": {
                        "string": "2016",
                        "period_type": "fiscalyear",
                        "currency_table_period_key": "_trial_balance_middle_periods",
                        "mode": "range",
                        "date_from": "2016-01-01",
                        "date_to": "2016-12-31",
                    },
                    "trial_balance_column_block_id": "0",
                    "trial_balance_column_type": "end_balance",
                    "trial_balance_block_fiscalyear_start": "2016-01-01",
                },
                "colspan": 1,
            },
            {
                "name": "Initial Balance",
                "forced_options": {
                    "date": {
                        "string": "As of 12/31/2016",
                        "period_type": "custom",
                        "currency_table_period_key": "_trial_balance_middle_periods",
                        "mode": "single",
                        "date_from": False,
                        "date_to": "2016-12-31",
                    },
                    "trial_balance_column_block_id": "1",
                    "trial_balance_column_type": "initial_balance",
                    "trial_balance_block_fiscalyear_start": "2017-01-01",
                },
                "colspan": 1,
            },
            {
                "name": "2017",
                "forced_options": {
                    "date": {
                        "string": "2017",
                        "period_type": "fiscalyear",
                        "currency_table_period_key": "_trial_balance_middle_periods",
                        "mode": "range",
                        "date_from": "2017-01-01",
                        "date_to": "2017-12-31",
                        "filter": "custom",
                    },
                },
            },
            {
                "name": "End Balance",
                "forced_options": {
                    "date": {
                        "string": "2017",
                        "period_type": "fiscalyear",
                        "currency_table_period_key": "_trial_balance_middle_periods",
                        "mode": "range",
                        "date_from": "2017-01-01",
                        "date_to": "2017-12-31",
                    },
                    "trial_balance_column_block_id": "1",
                    "trial_balance_column_type": "end_balance",
                    "trial_balance_block_fiscalyear_start": "2017-01-01",
                },
                "colspan": 1,
            },
        ]

        for i, val in enumerate(expected_header_values):
            self.assertDictEqual(options["column_headers"][0][i], val)

        # Rate for 2016 and 2017 is (1/3 (from 2016) * 366 + 1/2 (from 2017) * 365) / 731 => 0.416552668
        self.assertLinesValues(
            self.report._get_lines(options),
            #                                             [Initial Balance]   [     2016       ]    [End Balance]  [Initial Balance]      [       2017        ]       [End Balance]
            #    Name                                             Balance      Debit      Credit         Balance             Balance      Debit          Credit          Balance
            [0, 1, 2, 3, 4, 5, 6, 7, 8],
            [
                (
                    "121000 Account Receivable",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    1000.0,
                ),
                (
                    "211000 Account Payable",
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    100.0,
                    0.0,
                    0.0,
                    100.0,
                ),
                ("211010 Account Payable", 0.0, 50.0, 0.0, 50.0, 50.0, 0.0, 0.0, 50.0),
                (
                    "400000 Product Sales",
                    0.0,
                    0.0,
                    300.0,
                    -300.0,
                    0.0,
                    20000.0,
                    0.0,
                    20000.0,
                ),
                (
                    "400010 Product Sales",
                    0.0,
                    0.0,
                    41.66,
                    -41.66,
                    0.0,
                    0.0,
                    166.62,
                    -166.62,
                ),
                (
                    "600000 Expenses",
                    0.0,
                    200.0,
                    0.0,
                    200.0,
                    0.0,
                    0.0,
                    21000.0,
                    -21000.0,
                ),
                ("600010 Expenses", 0.0, 0.0, 0.0, 0.0, 0.0, 166.62, 0.0, 166.62),
                (
                    "Result Brought Forward - company_1_data",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -100.0,
                    0.0,
                    0.0,
                    -100.0,
                ),
                (
                    "Result Brought Forward - company_2",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -41.66,
                    0.0,
                    0.0,
                    -41.66,
                ),
                ("Total", 0.0, 350.0, 341.66, 8.34, 8.34, 21166.62, 21166.62, 8.34),
            ],
            options,
        )

    def test_trial_with_disabled_comparison_filter(self):
        self.report.filter_period_comparison = False
        options = self._generate_options(
            self.report,
            fields.Date.from_string("2017-01-01"),
            fields.Date.from_string("2017-12-31"),
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                                      Initial Balance        Debit        Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("121000 Account Receivable", 0.0, 1000.0, 0.0, 1000.0),
                ("211000 Account Payable", 100.0, 0.0, 0.0, 100.0),
                ("211010 Account Payable", 50.0, 0.0, 0.0, 50.0),
                ("400000 Product Sales", 0.0, 20000.0, 0.0, 20000.0),
                ("400010 Product Sales", 0.0, 0.0, 200.0, -200.0),
                ("600000 Expenses", 0.0, 0.0, 21000.0, -21000.0),
                ("600010 Expenses", 0.0, 200.0, 0.0, 200.0),
                ("Result Brought Forward - company_1_data", -100.0, 0.0, 0.0, -100.0),
                ("Result Brought Forward - company_2", -50.0, 0.0, 0.0, -50.0),
                ("Total", 0.0, 21200.0, 21200.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_account_group_with_hole(self):
        """
        The report must handle a hole in the account group hierarchy: groups 10 and
        1012 have entries while the intermediate group 101 has none.
        """

        test_journal = self.env["account.journal"].create(
            [
                {
                    "name": "test journal",
                    "code": "TJ",
                    "type": "general",
                }
            ]
        )

        self.env["account.group"].create(
            [
                {
                    "name": "Group_10",
                    "code_prefix_start": "10",
                    "code_prefix_end": "10",
                },
                {
                    "name": "Group_101",
                    "code_prefix_start": "101",
                    "code_prefix_end": "101",
                },
                {
                    "name": "Group_1012",
                    "code_prefix_start": "1012",
                    "code_prefix_end": "1012",
                },
            ]
        )

        # Create the accounts.
        account_a, account_a1 = self.env["account.account"].create(
            [
                {
                    "code": "100000",
                    "name": "Account A",
                    "account_type": "asset_current",
                },
                {
                    "code": "101200",
                    "name": "Account A1",
                    "account_type": "asset_current",
                },
            ]
        )

        move = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2017-06-01"),
                    "journal_id": test_journal.id,
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "account_a_1",
                                "account_id": account_a.id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "name": "account_a_2",
                                "account_id": account_a.id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 200.0,
                                "credit": 0.0,
                                "name": "account_a1_1",
                                "account_id": account_a1.id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 200.0,
                                "name": "account_a1_2",
                                "account_id": account_a1.id,
                            }
                        ),
                    ],
                }
            ]
        )
        move.action_post()

        options = self._generate_options(
            self.report,
            fields.Date.from_string("2017-06-01"),
            fields.Date.from_string("2017-06-01"),
        )
        options = self._update_multi_selector_filter(
            options, "journals", test_journal.ids
        )
        options["unfold_all"] = True

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                            Initial Balance         Debit          Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ["10 Group_10", 0.0, 300.0, 300.0, 0.0],
                ["100000 Account A", 0.0, 100.0, 100.0, 0.0],
                ["101 Group_101", 0.0, 200.0, 200.0, 0.0],
                ["1012 Group_1012", 0.0, 200.0, 200.0, 0.0],
                ["101200 Account A1", 0.0, 200.0, 200.0, 0.0],
                ["Total", 0.0, 300.0, 300.0, 0.0],
            ],
            options,
        )

    def test_action_general_ledger(self):
        """
        The caret_option_open_general_ledger action must set a default_filter_accounts
        and, when the hierarchy is enabled, unfold the group.
        """
        self.env["account.group"].create(
            [
                {"name": "Group_6", "code_prefix_start": "6", "code_prefix_end": "6"},
            ]
        )
        options = self._generate_options(
            self.report,
            "2017-06-01",
            "2017-06-01",
            default_options={"hierarchy": True, "unfold_all": True},
        )
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #    Name                                      Initial Balance        Debit        Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("6 Group_6", -21000.0, 200.0, 0.0, -20800.0),
                ("600000 Expenses", -21000.0, 0.0, 0.0, -21000.0),
                ("600010 Expenses", 0.0, 200.0, 0.0, 200.0),
                ("(No Group)", 21150.0, 0.0, 200.0, 20950.0),
                ("121000 Account Receivable", 1000.0, 0.0, 0.0, 1000.0),
                ("211000 Account Payable", 100.0, 0.0, 0.0, 100.0),
                ("211010 Account Payable", 50.0, 0.0, 0.0, 50.0),
                ("400000 Product Sales", 20000.0, 0.0, 0.0, 20000.0),
                ("400010 Product Sales", 0.0, 0.0, 200.0, -200.0),
                ("Result Brought Forward - company_1_data", -100.0, 0.0, 0.0, -100.0),
                ("Result Brought Forward - company_2", -50.0, 0.0, 0.0, -50.0),
                ("Total", 0.0, 200.0, 200.0, 0.0),
            ],
            options,
        )
        general_ledger = self.env.ref("account.general_ledger_report")
        params = {"line_id": lines[1]["id"]}
        res = self.report.caret_option_open_general_ledger(options, params)
        self.assertEqual(res["context"]["default_filter_accounts"], "600000")
        general_ledger_lines = general_ledger._get_lines(res["params"]["options"])
        unfolded_lines = [line for line in general_ledger_lines if line.get("unfolded")]
        self.assertEqual(len(unfolded_lines), 9)

    def test_action_general_ledger_unallocated_earnings(self):
        """
        caret_option_open_general_ledger on an Unallocated Earnings line, both in a
        multi-company scenario and with a single company selected.
        """
        options = self._generate_options(self.report, "2017-06-01", "2017-06-01")
        parent_line_id = self.report._get_generic_line_id(
            model_name="account.report.line",
            value=self.env.ref("account.trial_balance_report_all").id,
        )
        unallocated_earnings_line_id = self.report._get_generic_line_id(
            model_name="res.company",
            value=self.company_data["company"].id,
            parent_line_id=parent_line_id,
        )
        params = {"line_id": unallocated_earnings_line_id}

        # Test case with more than one company
        res = self.report.caret_option_open_general_ledger(options, params)
        self.assertEqual(
            res["context"]["default_filter_accounts"],
            "Result Brought Forward - company_1_data",
        )

        # Test case with only one company
        self.env.user.write(
            {
                "company_ids": [Command.set((self.company_data["company"]).ids)],
                "company_id": self.company_data["company"].id,
            }
        )
        res = self.report.caret_option_open_general_ledger(options, params)
        self.assertEqual(
            res["context"]["default_filter_accounts"], "Result Brought Forward"
        )

    def test_trial_balance_multiple_years_initial_balance(self):
        # Entries in 2015 for company_1 to test the initial balance for the Result Brought Forward line.
        move_2015_1 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.from_string("2015-01-01"),
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 50.0,
                            "credit": 0.0,
                            "name": "2015_1_1",
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 100.0,
                            "credit": 0.0,
                            "name": "2015_1_2",
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "debit": 0.0,
                            "credit": 150.0,
                            "name": "2015_1_3",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        },
                    ),
                ],
            }
        )
        move_2015_1.action_post()

        # Entry in 2016 for company_1 to test the initial balance for equity_unaffected accounts.
        equity_unaffected_acc = self.env["account.account"].search(
            [
                ("account_type", "=", "equity_unaffected"),
                ("company_ids", "in", self.company_data["company"].ids),
            ],
            order="code desc",
            limit=1,
        )
        move_2016_1 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.from_string("2016-01-01"),
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "debit": 70.0,
                            "credit": 0.0,
                            "name": "2016_1_1",
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
                            "credit": 70.0,
                            "name": "2016_1_2",
                            "account_id": equity_unaffected_acc.id,
                        },
                    ),
                ],
            }
        )
        move_2016_1.action_post()

        options = self._generate_options(self.report, "2017-01-01", "2017-12-31")
        options = self._update_comparison_filter(
            options,
            self.report,
            "previous_period",
            1,
            fields.Date.from_string("2017-01-01"),
            fields.Date.from_string("2017-12-31"),
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            #                                              [Initial Balance]   [     2016       ]    [End Balance]  [Initial Balance]      [       2017        ]       [End Balance]
            #    Name                                              Balance      Debit      Credit         Balance             Balance      Debit          Credit          Balance
            [0, 1, 2, 3, 4, 5, 6, 7, 8],
            [
                (
                    "121000 Account Receivable",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    1000.0,
                ),
                (
                    "211000 Account Payable",
                    50.0,
                    170.0,
                    0.0,
                    220.0,
                    220.0,
                    0.0,
                    0.0,
                    220.0,
                ),
                ("211010 Account Payable", 0.0, 50.0, 0.0, 50.0, 50.0, 0.0, 0.0, 50.0),
                (
                    "400000 Product Sales",
                    0.0,
                    0.0,
                    300.0,
                    -300.0,
                    0.0,
                    20000.0,
                    0.0,
                    20000.0,
                ),
                (
                    "400010 Product Sales",
                    0.0,
                    0.0,
                    41.66,
                    -41.66,
                    0.0,
                    0.0,
                    166.62,
                    -166.62,
                ),
                (
                    "600000 Expenses",
                    0.0,
                    200.0,
                    0.0,
                    200.0,
                    0.0,
                    0.0,
                    21000.0,
                    -21000.0,
                ),
                ("600010 Expenses", 0.0, 0.0, 0.0, 0.0, 0.0, 166.62, 0.0, 166.62),
                (
                    "999999 Profit or Loss Appropriation",
                    0.0,
                    0.0,
                    70.0,
                    -70.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                ),
                (
                    "Result Brought Forward - company_1_data",
                    -50.0,
                    0.0,
                    0.0,
                    -50.0,
                    -220.0,
                    0.0,
                    0.0,
                    -220.0,
                ),
                (
                    "Result Brought Forward - company_2",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -41.66,
                    0.0,
                    0.0,
                    -41.66,
                ),
                ("Total", 0.0, 420.0, 411.66, 8.34, 8.34, 21166.62, 21166.62, 8.34),
            ],
            options,
        )

    def test_trial_balance_comparisons_continuous_months(self):
        # Ensure that when comparing multiple months, an initial and end balance appear when the fiscal year changes.
        # Select only company 1 to avoid noise and focus on test objective.
        self.env.user.write(
            {
                "company_ids": [Command.set((self.company_data["company"]).ids)],
                "company_id": self.company_data["company"].id,
            }
        )

        options = self._generate_options(self.report, "2017-02-01", "2017-02-28")
        options = self._update_comparison_filter(
            options, self.report, comparison_type="previous_period", number_period=3
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            #                                             [Initial]  [  Nov 2016  ] [   Dec 2016  ] [ End ] [Initial ] [   Jan 2017  ] [  Feb 2017  ] [ End ]
            #    Name                                      Balance   Debit  Credit   Debit  Credit  Balance  Balance    Debit   Credit  Debit  Credit   Balance
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "121000 Account Receivable",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                ),
                (
                    "211000 Account Payable",
                    100.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    100.0,
                    100.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    100.0,
                ),
                (
                    "400000 Product Sales",
                    -300.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -300.0,
                    0.0,
                    20000.0,
                    0.0,
                    0.0,
                    0.0,
                    20000.0,
                ),
                (
                    "600000 Expenses",
                    200.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    200.0,
                    0.0,
                    0.0,
                    21000.0,
                    0.0,
                    0.0,
                    -21000.0,
                ),
                (
                    "Result Brought Forward",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -100.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -100.0,
                ),
                (
                    "Total",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    21000.0,
                    21000.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            ],
            options,
        )

    def test_trial_balance_comparisons_non_continuous_months(self):
        # Ensure that when comparing two non-continuous months, an end and initial balance columns are displayed.
        # Select only company 1 to avoid noise and focus on test objective.
        self.env.user.write(
            {
                "company_ids": [Command.set((self.company_data["company"]).ids)],
                "company_id": self.company_data["company"].id,
            }
        )

        options = self._generate_options(self.report, "2017-01-01", "2017-01-31")
        options = self._update_comparison_filter(
            options, self.report, comparison_type="same_last_year", number_period=1
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            #                                             [Initial]   [  Jan 2016  ]   [ End ]  [Initial ] [  Jan 2017   ]    [ End ]
            #    Name                                      Balance    Debit  Credit    Balance   Balance   Debit    Credit    Balance
            [0, 1, 2, 3, 4, 5, 6, 7, 8],
            [
                (
                    "121000 Account Receivable",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    1000.0,
                ),
                (
                    "211000 Account Payable",
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    100.0,
                    0.0,
                    0.0,
                    100.0,
                ),
                (
                    "400000 Product Sales",
                    0.0,
                    0.0,
                    300.0,
                    -300.0,
                    0.0,
                    20000.0,
                    0.0,
                    20000.0,
                ),
                (
                    "600000 Expenses",
                    0.0,
                    200.0,
                    0.0,
                    200.0,
                    0.0,
                    0.0,
                    21000.0,
                    -21000.0,
                ),
                (
                    "Result Brought Forward",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    -100.0,
                    0.0,
                    0.0,
                    -100.0,
                ),
                ("Total", 0.0, 300.0, 300.0, 0.0, 0.0, 21000.0, 21000.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_unfold_all(self):
        # Ensure the "unfold all" feature (and therefore the _custom_unfold_all_batch_data_generator) is working as expected
        # This also implies testing with multiple user groupbys. The key 'test_unfold_all' is provided to ensure that
        # no fallback is used in case a key is not provided by the custom unfold all function
        move_with_partner = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2017-01-31"),
                    "journal_id": self.company_data["default_journal_misc"].id,
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "aml_partner",
                                "partner_id": self.partner_a.id,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "name": "aml_partner_2",
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                            }
                        ),
                    ],
                }
            ]
        )
        move_with_partner.action_post()

        # Select only one company to reduce the number of lines
        self.env.user.write(
            {
                "company_ids": [Command.set((self.company_data["company"]).ids)],
                "company_id": self.company_data["company"].id,
            }
        )
        self.report.line_ids[0].user_groupby = "account_id, partner_id, id"

        options = self._generate_options(
            self.report,
            "2017-01-01",
            "2017-01-31",
            default_options={"unfold_all": True, "test_unfold_all": True},
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                                  Initial Balance       Debit          Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("121000 Account Receivable", 0.0, 1000.0, 0.0, 1000.0),
                ("Unknown", 0.0, 1000.0, 0.0, 1000.0),
                ("INV/2017/00001 2017_1_1", 0.0, 1000.0, 0.0, 1000.0),
                ("211000 Account Payable", 100.0, 0.0, 0.0, 100.0),
                ("Unknown", 100.0, 0.0, 0.0, 100.0),
                ("400000 Product Sales", 0.0, 20100.0, 0.0, 20100.0),
                ("partner_a", 0.0, 100.0, 0.0, 100.0),
                ("MISC/2017/01/0001 aml_partner", 0.0, 100.0, 0.0, 100.0),
                ("Unknown", 0.0, 20000.0, 0.0, 20000.0),
                ("INV/2017/00001 2017_1_2", 0.0, 2000.0, 0.0, 2000.0),
                ("INV/2017/00001 2017_1_3", 0.0, 3000.0, 0.0, 3000.0),
                ("INV/2017/00001 2017_1_4", 0.0, 4000.0, 0.0, 4000.0),
                ("INV/2017/00001 2017_1_5", 0.0, 5000.0, 0.0, 5000.0),
                ("INV/2017/00001 2017_1_6", 0.0, 6000.0, 0.0, 6000.0),
                ("600000 Expenses", 0.0, 0.0, 21100.0, -21100.0),
                ("Unknown", 0.0, 0.0, 21100.0, -21100.0),
                ("MISC/2017/01/0001 aml_partner_2", 0.0, 0.0, 100.0, -100.0),
                ("INV/2017/00001 2017_1_7", 0.0, 0.0, 6000.0, -6000.0),
                ("INV/2017/00001 2017_1_8", 0.0, 0.0, 7000.0, -7000.0),
                ("INV/2017/00001 2017_1_9", 0.0, 0.0, 8000.0, -8000.0),
                ("Result Brought Forward", -100.0, 0.0, 0.0, -100.0),
                ("Total", 0.0, 21100.0, 21100.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_audit_cell(self):
        """
        Audit of the trial balance cells, with a 2023 move on an expense account and
        the report opened in 2024 comparing with 2023. The move must be part of the
        audit domain of the 2023 expense cell and of the 2024 unaffected earnings
        cell, and absent from the two other cells.
        """
        move_1 = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2023-01-01"),
                    "journal_id": self.company_data["default_journal_misc"].id,
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "move_1_1",
                                "partner_id": self.partner_a.id,
                                "account_id": self.company_data[
                                    "default_account_assets"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "name": "move_1_2",
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                            }
                        ),
                    ],
                }
            ]
        )
        move_1.action_post()
        move_1_expense_line = move_1.line_ids[1]

        options = self._generate_options(
            self.report,
            "2024-01-01",
            "2024-12-31",
            default_options={
                "comparison": {
                    "filter": "previous_period",
                    "number_period": 1,
                    "period_order": "ascending",
                },
            },
        )

        lines = self.report._get_lines(options)
        unaff_line = next(
            line
            for line in lines
            if self.report._get_markup(line["id"]) == "undistributed_profits_losses"
        )
        expense_line = next(
            line
            for line in lines
            if line["name"] == self.company_data["default_account_expense"].display_name
        )
        trial_balance_top_parent_line = self.report.line_ids[0]

        end_balance_col_group_2023 = options["columns"][3]["column_group_key"]
        end_balance_col_group_2024 = options["columns"][7]["column_group_key"]

        # 1. Expense account in 2023
        params = self._get_audit_params_from_report_line(
            options,
            trial_balance_top_parent_line,
            expense_line,
            column_group_key=end_balance_col_group_2023,
        )
        audit_domain = self.report.dispatch_report_action(
            options, "action_audit_cell", params
        )["domain"]
        self.assertTrue(move_1_expense_line.filtered_domain(audit_domain))

        # 2. Unaffected account in 2023
        params = self._get_audit_params_from_report_line(
            options,
            trial_balance_top_parent_line,
            unaff_line,
            column_group_key=end_balance_col_group_2023,
        )
        audit_domain = self.report.dispatch_report_action(
            options, "action_audit_cell", params
        )["domain"]
        self.assertFalse(move_1_expense_line.filtered_domain(audit_domain))

        # 3. Expense account in 2024
        params = self._get_audit_params_from_report_line(
            options,
            trial_balance_top_parent_line,
            expense_line,
            column_group_key=end_balance_col_group_2024,
        )
        audit_domain = self.report.dispatch_report_action(
            options, "action_audit_cell", params
        )["domain"]
        self.assertFalse(move_1_expense_line.filtered_domain(audit_domain))

        # 4. Unaffected account in 2024
        params = self._get_audit_params_from_report_line(
            options,
            trial_balance_top_parent_line,
            unaff_line,
            column_group_key=end_balance_col_group_2024,
        )
        audit_domain = self.report.dispatch_report_action(
            options, "action_audit_cell", params
        )["domain"]
        self.assertTrue(move_1_expense_line.filtered_domain(audit_domain))

    def test_trial_balance_with_horizontal_groupby(self):
        horizontal_group = self.env["account.report.horizontal.group"].create(
            [
                {
                    "name": "Horizontal Group Products",
                    "report_ids": [self.report.id],
                    "rule_ids": [
                        Command.create(
                            {
                                "field_name": "partner_id",
                                "domain": f"[('id', 'in', {(self.partner_a + self.partner_b).ids})]",
                            }
                        ),
                    ],
                }
            ]
        )

        invoice = self._create_invoice_move("2017-01-31", self.partner_a.id)
        invoice.action_post()

        options = self._generate_options(
            self.report,
            fields.Date.from_string("2017-01-01"),
            fields.Date.from_string("2017-12-31"),
            default_options={
                "selected_horizontal_group_id": horizontal_group.id,
            },
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                            [           Initial Balance          ] [               2017                     ]  [              End Balance           ]
            #    Name                            [   Partner A   ]   [   Partner B    ]    [   Partner A   ]    [   Partner B    ]  [   Partner A   ]   [   Partner B    ]
            #    Name                            Debit      Credit    Debit      Credit    Debit      Credit    Debit      Credit    Debit      Credit    Debit      Credit
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "211000 Account Payable",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    0.0,
                    0.0,
                ),
                (
                    "Total",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    0.0,
                    0.0,
                    1000.0,
                    0.0,
                    0.0,
                    0.0,
                ),
            ],
            options,
        )

    def test_trial_balance_groupby_partner(self):
        """Make sure the trial balance still works properly when the first groupby isn't by account_id (but by partner_id for example)."""
        move_with_partner = self.env["account.move"].create(
            [
                {
                    "move_type": "entry",
                    "date": fields.Date.from_string("2017-01-31"),
                    "journal_id": self.company_data["default_journal_misc"].id,
                    "line_ids": [
                        Command.create(
                            {
                                "debit": 100.0,
                                "credit": 0.0,
                                "name": "aml_partner",
                                "partner_id": self.partner_a.id,
                                "account_id": self.company_data[
                                    "default_account_revenue"
                                ].id,
                            }
                        ),
                        Command.create(
                            {
                                "debit": 0.0,
                                "credit": 100.0,
                                "name": "aml_partner_2",
                                "partner_id": self.partner_a.id,
                                "account_id": self.company_data[
                                    "default_account_expense"
                                ].id,
                            }
                        ),
                    ],
                }
            ]
        )
        move_with_partner.action_post()

        # Select only one company to reduce the number of lines
        self.env.user.write(
            {
                "company_ids": [Command.set((self.company_data["company"]).ids)],
                "company_id": self.company_data["company"].id,
            }
        )
        self.report.line_ids[0].user_groupby = "partner_id, account_id, id"

        options = self._generate_options(
            self.report,
            "2017-01-01",
            "2017-01-31",
            default_options={"unfold_all": True, "test_unfold_all": True},
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                                  Initial Balance       Debit          Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("partner_a", 0.0, 100.0, 100.0, 0.0),
                ("400000 Product Sales", 0.0, 100.0, 0.0, 100.0),
                ("MISC/2017/01/0001 aml_partner", 0.0, 100.0, 0.0, 100.0),
                ("600000 Expenses", 0.0, 0.0, 100.0, -100.0),
                ("MISC/2017/01/0001 aml_partner_2", 0.0, 0.0, 100.0, -100.0),
                ("Unknown", 100.0, 21000.0, 21000.0, 100.0),
                ("121000 Account Receivable", 0.0, 1000.0, 0.0, 1000.0),
                ("INV/2017/00001 2017_1_1", 0.0, 1000.0, 0.0, 1000.0),
                ("211000 Account Payable", 100.0, 0.0, 0.0, 100.0),
                ("400000 Product Sales", 0.0, 20000.0, 0.0, 20000.0),
                ("INV/2017/00001 2017_1_2", 0.0, 2000.0, 0.0, 2000.0),
                ("INV/2017/00001 2017_1_3", 0.0, 3000.0, 0.0, 3000.0),
                ("INV/2017/00001 2017_1_4", 0.0, 4000.0, 0.0, 4000.0),
                ("INV/2017/00001 2017_1_5", 0.0, 5000.0, 0.0, 5000.0),
                ("INV/2017/00001 2017_1_6", 0.0, 6000.0, 0.0, 6000.0),
                ("600000 Expenses", 0.0, 0.0, 21000.0, -21000.0),
                ("INV/2017/00001 2017_1_7", 0.0, 0.0, 6000.0, -6000.0),
                ("INV/2017/00001 2017_1_8", 0.0, 0.0, 7000.0, -7000.0),
                ("INV/2017/00001 2017_1_9", 0.0, 0.0, 8000.0, -8000.0),
                ("Result Brought Forward", -100.0, 0.0, 0.0, -100.0),
                ("Total", 0.0, 21100.0, 21100.0, 0.0),
            ],
            options,
        )

    def test_blank_if_zero(self):
        """
        With the 'blank if zero' option, a '0.0' value is blanked on the account
        lines but kept on the total line.
        """
        self.report.column_ids.write({"blank_if_zero": True})
        options = self._generate_options(
            self.report,
            "2017-01-01",
            "2017-01-31",
            default_options={"unfold_all": True, "test_unfold_all": True},
        )
        options = self._update_multi_selector_filter(
            options, "journals", self.company_data["default_journal_sale"].ids
        )

        self.assertLinesValues(
            self.report._get_lines(options),
            #    Name                                  Initial Balance       Debit          Credit      End Balance
            [0, 1, 2, 3, 4],
            [
                ("121000 Account Receivable", "", 1000.0, "", 1000.0),
                ("400000 Product Sales", "", 20000.0, "", 20000.0),
                ("600000 Expenses", "", "", 21000.0, -21000.0),
                ("Total", 0.0, 21000.0, 21000.0, 0.0),
            ],
            options,
        )

    def test_trial_balance_analytic_groupby(self):
        """
        Test the groupby on analytic accounts and on analytic plans.
        """
        self.env.user.group_ids += self.env.ref("analytic.group_analytic_accounting")
        self.report.filter_analytic = True
        self.report.filter_analytic_groupby = True

        analytic_plan = self.env["account.analytic.plan"].create(
            {
                "name": "Plan XYZ",
            }
        )
        analytic_account = self.env["account.analytic.account"].create(
            {"name": "Account XYZ", "plan_id": analytic_plan.id}
        )
        move_2019 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.from_string("2019-01-01"),
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 50.0,
                            "credit": 0.0,
                            "name": "XYZ debit (2019)",
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                            "analytic_distribution": {analytic_account.id: 100},
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 50.0,
                            "name": "XYZ credit (2019)",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "analytic_distribution": {analytic_account.id: 100},
                        }
                    ),
                ],
            }
        )
        move_2019.action_post()
        move_2020 = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.from_string("2020-01-01"),
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 100.0,
                            "credit": 0.0,
                            "name": "XYZ debit (2020)",
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                            "analytic_distribution": {analytic_account.id: 100},
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 100.0,
                            "name": "XYZ credit (2020)",
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "analytic_distribution": {analytic_account.id: 100},
                        }
                    ),
                ],
            }
        )
        move_2020.action_post()

        # add a group by analytic account
        options = self._generate_options(
            self.report,
            "2020-01-01",
            "2020-01-31",
            default_options={
                "analytic_accounts": [analytic_account.id],
                "analytic_accounts_groupby": [analytic_account.id],
            },
        )
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #                                                       [         Initial Balance        ]    [            Jan 2020            ]    [           End Balance          ]
            #                                                       [ Account XYZ ]    [    Total    ]    [ Account XYZ ]    [    Total    ]    [ Account XYZ ]    [    Total    ]
            #   Name                                                Debit    Credit    Debit    Credit    Debit    Credit    Debit    Credit    Debit    Credit    Debit    Credit
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "211000 Account Payable",
                    50.0,
                    0.0,
                    50.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    0.0,
                    150.0,
                    0.0,
                    150.0,
                    0.0,
                ),
                (
                    "400000 Product Sales",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                ),
                (
                    "Result Brought Forward - company_1_data",
                    0.0,
                    50.0,
                    0.0,
                    50.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    50.0,
                    0.0,
                    50.0,
                ),
                (
                    "Total",
                    50.0,
                    50.0,
                    50.0,
                    50.0,
                    100.0,
                    100.0,
                    100.0,
                    100.0,
                    150.0,
                    150.0,
                    150.0,
                    150.0,
                ),
            ],
            options,
        )

        # add a group by analytic plan
        options = self._generate_options(
            self.report,
            "2020-01-01",
            "2020-01-31",
            default_options={
                "analytic_accounts": [analytic_account.id],
                "analytic_plans_groupby": [analytic_plan.id],
            },
        )
        lines = self.report._get_lines(options)
        self.assertLinesValues(
            lines,
            #                                                      [         Initial Balance        ]    [            Jan 2020            ]    [           End Balance          ]
            #                                                      [   Plan XYZ  ]    [    Total    ]    [   Plan XYZ  ]    [    Total    ]    [   Plan XYZ  ]    [    Total    ]
            #   Name                                               Debit    Credit    Debit    Credit    Debit    Credit    Debit    Credit    Debit    Credit    Debit    Credit
            [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            [
                (
                    "211000 Account Payable",
                    50.0,
                    0.0,
                    50.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    0.0,
                    150.0,
                    0.0,
                    150.0,
                    0.0,
                ),
                (
                    "400000 Product Sales",
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                    0.0,
                    100.0,
                ),
                (
                    "Result Brought Forward - company_1_data",
                    0.0,
                    50.0,
                    0.0,
                    50.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    0.0,
                    50.0,
                    0.0,
                    50.0,
                ),
                (
                    "Total",
                    50.0,
                    50.0,
                    50.0,
                    50.0,
                    100.0,
                    100.0,
                    100.0,
                    100.0,
                    150.0,
                    150.0,
                    150.0,
                    150.0,
                ),
            ],
            options,
        )

    def test_export_xlsx_with_inf_account_code(self):
        account_with_inf_code = self.env["account.account"].create(
            [{"code": "1E1000", "name": "", "account_type": "asset_receivable"}]
        )
        move = self.env["account.move"].create(
            {
                "date": "2025-08-02",
                "line_ids": [
                    Command.create({"account_id": account_with_inf_code.id, "name": ""})
                ],
            }
        )
        move.action_post()
        options = self._generate_options(
            self.report,
            fields.Date.from_string("2025-08-01"),
            fields.Date.from_string("2025-08-31"),
        )
        self.report.export_to_xlsx(options)

    def test_trial_balance_export_pdf_filter(self):
        """
        The search bar filter must apply on the account code, the account name and,
        when the hierarchy is enabled, on the group name; also on undistributed
        profits/losses.
        """
        self.env.lang = self.env["res.lang"].search([("code", "=", "en_US")]).code
        self.env["account.group"].create(
            [
                {
                    "name": "Group_10",
                    "code_prefix_start": "10",
                    "code_prefix_end": "10",
                },
                {
                    "name": "Group_101",
                    "code_prefix_start": "101",
                    "code_prefix_end": "101",
                },
                {
                    "name": "Group_1012",
                    "code_prefix_start": "1012",
                    "code_prefix_end": "1012",
                },
                {
                    "name": "Group_102",
                    "code_prefix_start": "102",
                    "code_prefix_end": "102",
                },
            ]
        )

        # Create the accounts.
        account_a, account_a1, account_b2 = self.env["account.account"].create(
            [
                {
                    "code": "100000",
                    "name": "Account A",
                    "account_type": "asset_current",
                },
                {
                    "code": "101200",
                    "name": "Account A1",
                    "account_type": "asset_current",
                },
                {
                    "code": "102200",
                    "name": "Account B2",
                    "account_type": "asset_current",
                },
            ]
        )

        move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": fields.Date.from_string("2017-06-01"),
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "debit": 100.0,
                            "credit": 0.0,
                            "name": "account_a_1",
                            "account_id": account_a.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 100.0,
                            "name": "account_a_2",
                            "account_id": account_a.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 200.0,
                            "credit": 0.0,
                            "name": "account_a1_1",
                            "account_id": account_a1.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 200.0,
                            "name": "account_a1_2",
                            "account_id": account_a1.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 333.0,
                            "credit": 0.0,
                            "name": "account_b2_1",
                            "account_id": account_b2.id,
                        }
                    ),
                    Command.create(
                        {
                            "debit": 0.0,
                            "credit": 333.0,
                            "name": "account_b2_2",
                            "account_id": account_b2.id,
                        }
                    ),
                ],
            }
        )
        move.action_post()

        # Test the filter on account_code
        default_options = {
            "hierarchy": False,
            "unfold_all": True,
            "export_mode": "print",
            "filter_search_bar": "101",
        }
        options = self._generate_options(
            self.report, "2017-06-01", "2017-06-01", default_options=default_options
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [0, 1, 2, 3, 4],
            [
                ["101200 Account A1", 0.0, 200.0, 200.0, 0.0],
                ["Total", 0.0, 200.0, 200.0, 0.0],
            ],
            options,
        )

        # Test the filter on account_name
        default_options = {
            "hierarchy": False,
            "unfold_all": True,
            "export_mode": "print",
            "filter_search_bar": "Account A",
        }
        options = self._generate_options(
            self.report, "2017-06-01", "2017-06-01", default_options=default_options
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [0, 1, 2, 3, 4],
            [
                ["100000 Account A", 0.0, 100.0, 100.0, 0.0],
                ["101200 Account A1", 0.0, 200.0, 200.0, 0.0],
                ["Total", 0.0, 300.0, 300.0, 0.0],
            ],
            options,
        )

        # Test the filter on account_group and account_code
        default_options = {
            "hierarchy": True,
            "unfold_all": True,
            "export_mode": "print",
            "filter_search_bar": "Group_101",
        }
        options = self._generate_options(
            self.report, "2017-06-01", "2017-06-01", default_options=default_options
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [0, 1, 2, 3, 4],
            [
                ["10 Group_10", 0.0, 200.0, 200.0, 0.0],
                ["101 Group_101", 0.0, 200.0, 200.0, 0.0],
                ["1012 Group_1012", 0.0, 200.0, 200.0, 0.0],
                ["101200 Account A1", 0.0, 200.0, 200.0, 0.0],
                ["Total", 0.0, 200.0, 200.0, 0.0],
            ],
            options,
        )

        # Test the filter on undistributed profits/losses
        default_options = {
            "unfold_all": True,
            "export_mode": "print",
            "filter_search_bar": "result brought forward",
        }
        options = self._generate_options(
            self.report, "2017-06-01", "2017-06-01", default_options=default_options
        )
        self.assertLinesValues(
            self.report._get_lines(options),
            [0, 1, 2, 3, 4],
            [
                ["Result Brought Forward - company_1_data", -100.0, 0.0, 0.0, -100.0],
                ["Result Brought Forward - company_2", -50.0, 0.0, 0.0, -50.0],
                ["Total", -150.0, 0.0, 0.0, -150.0],
            ],
            options,
        )

    def test_open_journal_items_on_account_group(self):
        """Drilling into an account.group line must resolve to the accounts under
        that group.
        """
        # Regression: under psycopg3 the `code_store->>'%(root_company_id)s'` lookup
        # used a placeholder *inside* a SQL string literal, which is not substituted,
        # so it read the literal jsonb key '%s', matched no account, and left the
        # drill-down domain empty (clicking a group showed no journal items).
        group = self.env["account.group"].create(
            {
                "name": "Regr Group",
                "code_prefix_start": "404",
                "code_prefix_end": "404",
            }
        )
        account = self.env["account.account"].create(
            {
                "code": "404200",
                "name": "Regr Account",
                "account_type": "asset_current",
            }
        )
        options = self._generate_options(self.report, "2017-01-01", "2017-12-31")
        line_id = self.report._get_generic_line_id("account.group", group.id)
        action = self.report.open_journal_items(options, {"line_id": line_id})

        account_leaves = [
            leaf
            for leaf in action["domain"]
            if leaf[0] == "account_id" and leaf[1] == "in"
        ]
        self.assertTrue(
            account_leaves, "the drill-down must filter journal items by account"
        )
        self.assertIn(
            account.id,
            account_leaves[0][2],
            "the account under the clicked group must be part of the drill-down domain",
        )
