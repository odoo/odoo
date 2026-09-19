import base64

from odoo import Command, fields
from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountBankStatementLine(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.currency_1 = cls.company_data["currency"]
        cls.currency_2 = cls.setup_other_currency("EUR")
        cls.currency_3 = cls.setup_other_currency(
            "CAD", rates=[("2016-01-01", 6.0), ("2017-01-01", 4.0)]
        )
        cls.currency_4 = cls.setup_other_currency(
            "GBP", rates=[("2016-01-01", 12.0), ("2017-01-01", 8.0)]
        )

        cls.company_data_2 = cls.setup_other_company()

        cls.bank_journal_1 = cls.company_data["default_journal_bank"]
        cls.bank_journal_2 = cls.bank_journal_1.copy()
        cls.bank_journal_3 = cls.bank_journal_2.copy()

        cls.statement = cls.env["account.bank.statement"].create(
            {
                "name": "test_statement",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "date": "2019-01-01",
                            "payment_ref": "line_1",
                            "partner_id": cls.partner_a.id,
                            "foreign_currency_id": cls.currency_2.id,
                            "journal_id": cls.bank_journal_1.id,
                            "amount": 1250.0,
                            "amount_currency": 2500.0,
                        },
                    ),
                ],
            }
        )
        cls.statement_line = cls.statement.line_ids

        cls.expected_st_line = {
            "date": fields.Date.from_string("2019-01-01"),
            "journal_id": cls.statement.journal_id.id,
            "payment_ref": "line_1",
            "partner_id": cls.partner_a.id,
            "currency_id": cls.currency_1.id,
            "foreign_currency_id": cls.currency_2.id,
            "amount": 1250.0,
            "amount_currency": 2500.0,
            "is_reconciled": False,
        }

        cls.expected_bank_line = {
            "name": cls.statement_line.payment_ref,
            "partner_id": cls.statement_line.partner_id.id,
            "currency_id": cls.currency_1.id,
            "account_id": cls.statement.journal_id.default_account_id.id,
            "debit": 1250.0,
            "credit": 0.0,
            "amount_currency": 1250.0,
        }

        cls.expected_counterpart_line = {
            "name": cls.statement_line.payment_ref,
            "partner_id": cls.statement_line.partner_id.id,
            "currency_id": cls.currency_2.id,
            "account_id": cls.statement.journal_id.suspense_account_id.id,
            "debit": 0.0,
            "credit": 1250.0,
            "amount_currency": -2500.0,
        }

    def assertBankStatementLine(
        self, statement_line, expected_statement_line_vals, expected_move_line_vals
    ):
        self.assertRecordValues(statement_line, [expected_statement_line_vals])
        self.assertRecordValues(
            statement_line.line_ids.sorted("balance"), expected_move_line_vals
        )

    def create_bank_transaction(
        self,
        amount,
        date,
        amount_currency=None,
        currency=None,
        statement=None,
        partner=None,
        journal=None,
        sequence=0,
    ):
        values = {
            "payment_ref": str(amount),
            "amount": amount,
            "date": date,
            "partner_id": partner and partner.id,
            "sequence": sequence,
        }
        if amount_currency:
            values["amount_currency"] = amount_currency
            values["foreign_currency_id"] = currency.id
        if statement and journal and statement.journal_id != journal:
            raise (ValidationError("The statement and the journal are contradictory"))
        if statement:
            values["journal_id"] = statement.journal_id.id
            values["statement_id"] = statement.id
        if journal:
            values["journal_id"] = journal.id
        if not values.get("journal_id"):
            values["journal_id"] = (
                self.company_data_2["default_journal_bank"]
                if self.env.company == self.company_data_2["company"]
                else self.company_data["default_journal_bank"]
            ).id
        return self.env["account.bank.statement.line"].create(values)

    def _test_statement_line_edition(
        self,
        journal,
        amount,
        amount_currency,
        journal_currency,
        foreign_currency,
        expected_liquidity_values,
        expected_counterpart_values,
    ):
        if journal_currency:
            journal.currency_id = journal_currency.id

        statement_line = self.env["account.bank.statement.line"].create(
            {
                "date": "2019-01-01",
                "journal_id": journal.id,
                "payment_ref": "line_1",
                "partner_id": self.partner_a.id,
                "foreign_currency_id": foreign_currency and foreign_currency.id,
                "amount": amount,
                "amount_currency": amount_currency,
            }
        )

        self.assertRecordValues(
            statement_line,
            [
                {
                    "amount": amount,
                    "amount_currency": amount_currency,
                }
            ],
        )
        self.assertRecordValues(
            statement_line.move_id,
            [
                {
                    "partner_id": self.partner_a.id,
                    "currency_id": (
                        statement_line.foreign_currency_id or statement_line.currency_id
                    ).id,
                }
            ],
        )

        liquidity_lines, suspense_lines, _other_lines = statement_line._seek_for_lines()
        self.assertRecordValues(liquidity_lines, [expected_liquidity_values])
        self.assertRecordValues(suspense_lines, [expected_counterpart_values])

        statement_line.write(
            {
                "amount": statement_line.amount * 2,
                "amount_currency": statement_line.amount_currency * 2,
            }
        )
        self.assertRecordValues(
            statement_line,
            [
                {
                    "amount": amount * 2,
                    "amount_currency": amount_currency * 2,
                }
            ],
        )
        self.assertRecordValues(
            liquidity_lines,
            [
                {
                    **expected_liquidity_values,
                    "debit": expected_liquidity_values.get("debit", 0.0) * 2,
                    "credit": expected_liquidity_values.get("credit", 0.0) * 2,
                    "amount_currency": expected_liquidity_values.get(
                        "amount_currency", 0.0
                    )
                    * 2,
                }
            ],
        )
        self.assertRecordValues(
            suspense_lines,
            [
                {
                    "debit": expected_counterpart_values.get("debit", 0.0) * 2,
                    "credit": expected_counterpart_values.get("credit", 0.0) * 2,
                    "amount_currency": expected_counterpart_values.get(
                        "amount_currency", 0.0
                    )
                    * 2,
                }
            ],
        )

        statement_line.move_id.with_context(skip_readonly_check=True).write(
            {
                "line_ids": [
                    (
                        1,
                        liquidity_lines.id,
                        {
                            "debit": expected_liquidity_values.get("debit", 0.0),
                            "credit": expected_liquidity_values.get("credit", 0.0),
                            "amount_currency": expected_liquidity_values.get(
                                "amount_currency", 0.0
                            ),
                        },
                    ),
                    (
                        1,
                        suspense_lines.id,
                        {
                            "debit": expected_counterpart_values.get("debit", 0.0),
                            "credit": expected_counterpart_values.get("credit", 0.0),
                            "amount_currency": expected_counterpart_values.get(
                                "amount_currency", 0.0
                            ),
                        },
                    ),
                ]
            }
        )
        self.assertRecordValues(
            statement_line,
            [
                {
                    "amount": amount,
                    "amount_currency": amount_currency,
                }
            ],
        )

    def _test_edition_customer_and_supplier_flows(
        self,
        amount,
        amount_currency,
        journal_currency,
        foreign_currency,
        expected_liquidity_values,
        expected_counterpart_values,
    ):
        self._test_statement_line_edition(
            self.bank_journal_2,
            amount,
            amount_currency,
            journal_currency,
            foreign_currency,
            expected_liquidity_values,
            expected_counterpart_values,
        )

        self._test_statement_line_edition(
            self.bank_journal_3,
            -amount,
            -amount_currency,
            journal_currency,
            foreign_currency,
            {
                **expected_liquidity_values,
                "debit": expected_liquidity_values.get("credit", 0.0),
                "credit": expected_liquidity_values.get("debit", 0.0),
                "amount_currency": -expected_liquidity_values.get(
                    "amount_currency", 0.0
                ),
            },
            {
                **expected_counterpart_values,
                "debit": expected_counterpart_values.get("credit", 0.0),
                "credit": expected_counterpart_values.get("debit", 0.0),
                "amount_currency": -expected_counterpart_values.get(
                    "amount_currency", 0.0
                ),
            },
        )

    def test_edition_journal_curr_2_statement_curr_3(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,
            120.0,
            self.currency_2,
            self.currency_3,
            {
                "debit": 40.0,
                "credit": 0.0,
                "amount_currency": 80.0,
                "currency_id": self.currency_2.id,
            },
            {
                "debit": 0.0,
                "credit": 40.0,
                "amount_currency": -120.0,
                "currency_id": self.currency_3.id,
            },
        )

    def test_edition_journal_curr_2_statement_curr_1(self):
        self._test_edition_customer_and_supplier_flows(
            120.0,
            80.0,
            self.currency_2,
            self.currency_1,
            {
                "debit": 80.0,
                "credit": 0.0,
                "amount_currency": 120.0,
                "currency_id": self.currency_2.id,
            },
            {
                "debit": 0.0,
                "credit": 80.0,
                "amount_currency": -80.0,
                "currency_id": self.currency_1.id,
            },
        )

    def test_edition_journal_curr_1_statement_curr_2(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,
            120.0,
            self.currency_1,
            self.currency_2,
            {
                "debit": 80.0,
                "credit": 0.0,
                "amount_currency": 80.0,
                "currency_id": self.currency_1.id,
            },
            {
                "debit": 0.0,
                "credit": 80.0,
                "amount_currency": -120.0,
                "currency_id": self.currency_2.id,
            },
        )

    def test_edition_journal_curr_2_statement_false(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,
            0.0,
            self.currency_2,
            False,
            {
                "debit": 40.0,
                "credit": 0.0,
                "amount_currency": 80.0,
                "currency_id": self.currency_2.id,
            },
            {
                "debit": 0.0,
                "credit": 40.0,
                "amount_currency": -80.0,
                "currency_id": self.currency_2.id,
            },
        )

    def test_edition_journal_curr_1_statement_false(self):
        self._test_edition_customer_and_supplier_flows(
            80.0,
            0.0,
            self.currency_1,
            False,
            {
                "debit": 80.0,
                "credit": 0.0,
                "amount_currency": 80.0,
                "currency_id": self.currency_1.id,
            },
            {
                "debit": 0.0,
                "credit": 80.0,
                "amount_currency": -80.0,
                "currency_id": self.currency_1.id,
            },
        )

    def test_zero_amount_journal_curr_1_statement_curr_2(self):
        self.bank_journal_2.currency_id = self.currency_1

        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal_2.id,
                "date": "2019-01-01",
                "payment_ref": "line_1",
                "partner_id": self.partner_a.id,
                "foreign_currency_id": self.currency_2.id,
                "amount": 0.0,
                "amount_currency": 10.0,
            }
        )

        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": self.currency_1.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -10.0,
                    "currency_id": self.currency_2.id,
                },
            ],
        )

    def test_zero_amount_journal_curr_2_statement_curr_1(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal_2.id,
                "date": "2019-01-01",
                "payment_ref": "line_1",
                "partner_id": self.partner_a.id,
                "foreign_currency_id": self.currency_1.id,
                "amount": 0.0,
                "amount_currency": 10.0,
            }
        )

        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "debit": 10.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": self.currency_2.id,
                },
                {
                    "debit": 0.0,
                    "credit": 10.0,
                    "amount_currency": -10.0,
                    "currency_id": self.currency_1.id,
                },
            ],
        )

    def test_zero_amount_journal_curr_2_statement_curr_3(self):
        self.bank_journal_2.currency_id = self.currency_2

        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal_2.id,
                "date": "2019-01-01",
                "payment_ref": "line_1",
                "partner_id": self.partner_a.id,
                "foreign_currency_id": self.currency_3.id,
                "amount": 0.0,
                "amount_currency": 10.0,
            }
        )

        self.assertRecordValues(
            statement_line.move_id.line_ids,
            [
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": 0.0,
                    "currency_id": self.currency_2.id,
                },
                {
                    "debit": 0.0,
                    "credit": 0.0,
                    "amount_currency": -10.0,
                    "currency_id": self.currency_3.id,
                },
            ],
        )

    def test_constraints(self):
        def assertStatementLineConstraint(statement_line_vals):
            with self.assertRaises(Exception):
                self.env["account.bank.statement.line"].create(statement_line_vals)

        statement_line_vals = {
            "journal_id": self.bank_journal_2.id,
            "date": "2019-01-01",
            "payment_ref": "line_1",
            "partner_id": self.partner_a.id,
            "foreign_currency_id": False,
            "amount": 10.0,
            "amount_currency": 0.0,
        }

        assertStatementLineConstraint(
            {
                **statement_line_vals,
                "amount_currency": 10.0,
            }
        )

        assertStatementLineConstraint(
            {
                **statement_line_vals,
                "foreign_currency_id": self.currency_2.id,
            }
        )

        st_line = self.env["account.bank.statement.line"].create(statement_line_vals)

        addition_lines_to_create = [
            {
                "debit": 1.0,
                "credit": 0,
                "account_id": self.bank_journal_2.default_account_id.id,
                "move_id": st_line.move_id.id,
            },
            {
                "debit": 0,
                "credit": 1.0,
                "account_id": self.company_data["default_account_revenue"].id,
                "move_id": st_line.move_id.id,
            },
        ]
        with self.assertRaises(UserError):
            st_line.move_id.write(
                {"line_ids": [(0, 0, vals) for vals in addition_lines_to_create]}
            )

        with self.assertRaises(UserError):
            st_line.line_ids.create(addition_lines_to_create)

    def test_statement_line_move_onchange_1(self):
        self.assertBankStatementLine(
            self.statement_line,
            self.expected_st_line,
            [self.expected_counterpart_line, self.expected_bank_line],
        )

        self.statement_line.write(
            {
                "amount": -2000.0,
                "amount_currency": -4000.0,
                "foreign_currency_id": self.currency_3.id,
            }
        )

        self.assertBankStatementLine(
            self.statement_line,
            {
                **self.expected_st_line,
                "amount": -2000.0,
                "amount_currency": -4000.0,
                "foreign_currency_id": self.currency_3.id,
            },
            [
                {
                    **self.expected_bank_line,
                    "debit": 0.0,
                    "credit": 2000.0,
                    "amount_currency": -2000.0,
                    "currency_id": self.currency_1.id,
                },
                {
                    **self.expected_counterpart_line,
                    "debit": 2000.0,
                    "credit": 0.0,
                    "amount_currency": 4000.0,
                    "currency_id": self.currency_3.id,
                },
            ],
        )

        self.statement_line.write(
            {
                "payment_ref": "line_1 (bis)",
                "partner_id": self.partner_b.id,
            }
        )

        self.assertBankStatementLine(
            self.statement_line,
            {
                **self.expected_st_line,
                "payment_ref": self.statement_line.payment_ref,
                "partner_id": self.statement_line.partner_id.id,
                "amount": -2000.0,
                "amount_currency": -4000.0,
                "foreign_currency_id": self.currency_3.id,
            },
            [
                {
                    **self.expected_bank_line,
                    "name": self.statement_line.payment_ref,
                    "partner_id": self.statement_line.partner_id.id,
                    "debit": 0.0,
                    "credit": 2000.0,
                    "amount_currency": -2000.0,
                    "currency_id": self.currency_1.id,
                },
                {
                    **self.expected_counterpart_line,
                    "name": self.statement_line.payment_ref,
                    "partner_id": self.statement_line.partner_id.id,
                    "debit": 2000.0,
                    "credit": 0.0,
                    "amount_currency": 4000.0,
                    "currency_id": self.currency_3.id,
                },
            ],
        )

    def test_prepare_counterpart_amounts_using_st_line_rate(self):
        def assertAppliedRate(
            journal_currency,
            foreign_currency,
            aml_currency,
            amount,
            amount_currency,
            aml_amount_currency,
            aml_balance,
            expected_amount_currency,
            expected_balance,
        ):
            journal = self.bank_journal_1.copy()
            journal.currency_id = journal_currency

            statement_line = self.env["account.bank.statement.line"].create(
                {
                    "journal_id": journal.id,
                    "date": "2019-01-01",
                    "payment_ref": "test_prepare_counterpart_amounts_using_st_line_rate",
                    "foreign_currency_id": foreign_currency.id
                    if foreign_currency != journal_currency
                    else None,
                    "amount": amount,
                    "amount_currency": amount_currency
                    if foreign_currency != journal_currency
                    else 0.0,
                }
            )

            res = statement_line._prepare_counterpart_amounts_using_st_line_rate(
                aml_currency, -aml_balance, -aml_amount_currency
            )
            self.assertAlmostEqual(res["amount_currency"], expected_amount_currency)
            self.assertAlmostEqual(res["balance"], expected_balance)

        for params in (
            (
                self.currency_2,
                self.currency_3,
                self.currency_3,
                80.0,
                120.0,
                120.0,
                20.0,
                -120.0,
                -40.0,
            ),
            (
                self.currency_2,
                self.currency_1,
                self.currency_2,
                120.0,
                80.0,
                120.0,
                40.0,
                -80.0,
                -80.0,
            ),
            (
                self.currency_2,
                self.currency_3,
                self.currency_2,
                80.0,
                120.0,
                80.0,
                26.67,
                -120.0,
                -40.0,
            ),
            (
                self.currency_2,
                self.currency_3,
                self.currency_4,
                80.0,
                120.0,
                480.0,
                40.0,
                -120.0,
                -40.0,
            ),
            (
                self.currency_1,
                self.currency_2,
                self.currency_2,
                80.0,
                120.0,
                120.0,
                40.0,
                -120.0,
                -80.0,
            ),
            (
                self.currency_1,
                self.currency_2,
                self.currency_3,
                80.0,
                120.0,
                480.0,
                80.0,
                -120.0,
                -80.0,
            ),
            (
                self.currency_2,
                self.currency_2,
                self.currency_2,
                80.0,
                80.0,
                80.0,
                26.67,
                -80.0,
                -40.0,
            ),
            (
                self.currency_2,
                self.currency_2,
                self.currency_3,
                80.0,
                80.0,
                240.0,
                40.0,
                -80.0,
                -40.0,
            ),
            (
                self.currency_1,
                self.currency_1,
                self.currency_3,
                80.0,
                80.0,
                480.0,
                80.0,
                -80.0,
                -80.0,
            ),
            (
                self.currency_2,
                self.currency_1,
                self.currency_1,
                120.0,
                80.0,
                80.0,
                80.0,
                -80.0,
                -80.0,
            ),
            (
                self.currency_2,
                self.currency_3,
                self.currency_1,
                80.0,
                120.0,
                40.0,
                40.0,
                -120.0,
                -40.0,
            ),
            (
                self.currency_1,
                self.currency_2,
                self.currency_1,
                80.0,
                120.0,
                80.0,
                80.0,
                -120.0,
                -80.0,
            ),
            (
                self.currency_2,
                self.currency_2,
                self.currency_1,
                80.0,
                80.0,
                40.0,
                40.0,
                -80.0,
                -40.0,
            ),
            (
                self.currency_1,
                self.currency_1,
                self.currency_1,
                80.0,
                80.0,
                80.0,
                80.0,
                -80.0,
                -80.0,
            ),
        ):
            with self.subTest(params=params):
                assertAppliedRate(*params)

    def test_for_presence_single_suspense_line(self):
        statement_line = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.bank_journal_3.id,
                "date": "2019-01-01",
                "payment_ref": "line_1",
                "amount": 0.0,
            }
        )

        with self.assertRaises(UserError):
            statement_line.line_ids = [
                Command.create(
                    {
                        "account_id": statement_line.journal_id.suspense_account_id.id,
                        "balance": 0.0,
                    }
                )
            ]

    def test_zero_amount_statement_line(self):
        self.company_data[
            "company"
        ].account_config_id.account_journal_suspense_account_id.reconcile = False

        statement = (
            self.env["account.bank.statement"]
            .with_context(skip_check_amounts_currencies=True)
            .create(
                {
                    "name": "test_statement",
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "date": "2019-01-01",
                                "payment_ref": "Happy new year",
                                "amount": 0.0,
                                "journal_id": self.bank_journal_2.id,
                            },
                        ),
                    ],
                }
            )
        )
        statement_line = statement.line_ids

        self.assertRecordValues(
            statement_line, [{"is_reconciled": True, "amount_residual": 0.0}]
        )

    def test_statement_valid_complete_1(self):
        self.env.user.company_id = self.company_data_2["company"]

        line1 = self.create_bank_transaction(1, "2020-01-10")
        line2 = self.create_bank_transaction(2, "2020-01-11")
        statement1 = (
            self.env["account.bank.statement"]
            .with_context(st_line_id=line1.id, active_ids=[line1.id, line2.id])
            .create({})
        )
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "is_valid": True,
                    "balance_start": 0,
                    "balance_end": 3,
                    "balance_end_real": 3,
                }
            ],
        )
        line1.statement_id = False
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": False,
                    "is_valid": True,
                    "balance_start": 0,
                    "balance_end": 2,
                    "balance_end_real": 3,
                }
            ],
        )
        line3 = self.create_bank_transaction(1, "2020-01-12", statement=statement1)
        statement1.invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        statement2 = self.env["account.bank.statement"].create(
            {
                "line_ids": [Command.set(line1.ids)],
                "balance_end_real": 1,
            }
        )
        (statement1 + statement2).invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1 + statement2,
            [
                {
                    "is_complete": True,
                    "is_valid": False,
                },
                {
                    "is_complete": True,
                    "is_valid": True,
                },
            ],
        )
        statement1.balance_start = 1
        statement1.invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        statement2.balance_end_real = 10
        statement2.flush_recordset(["balance_end_real"])
        statement1.invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "is_valid": False,
                }
            ],
        )
        statement1.write({"balance_start": 10, "balance_end_real": 3})
        statement1.invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": False,
                    "is_valid": True,
                }
            ],
        )
        line4 = self.create_bank_transaction(-10, "2020-01-13", statement=statement1)
        (statement1 + statement2).invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1 + statement2,
            [
                {
                    "is_complete": True,
                    "is_valid": True,
                    "date": fields.Date.from_string("2020-01-13"),
                },
                {
                    "is_complete": False,
                    "is_valid": True,
                    "date": fields.Date.from_string("2020-01-10"),
                },
            ],
        )
        self.assertRecordValues(
            line1 + line2 + line3 + line4,
            [
                {
                    "date": fields.Date.from_string("2020-01-10"),
                    "statement_id": statement2.id,
                },
                {
                    "date": fields.Date.from_string("2020-01-11"),
                    "statement_id": statement1.id,
                },
                {
                    "date": fields.Date.from_string("2020-01-12"),
                    "statement_id": statement1.id,
                },
                {
                    "date": fields.Date.from_string("2020-01-13"),
                    "statement_id": statement1.id,
                },
            ],
        )

        statement2.balance_end_real = 100
        statement2.flush_recordset(["balance_end_real"])
        statement1.invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_valid": False,
                }
            ],
        )
        line1.statement_id = False
        line1.flush_model()
        statement2.flush_model()
        statement1.invalidate_model(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_valid": True,
                }
            ],
        )

        line3.statement_id = False
        statement1.flush_recordset(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_valid": True,
                }
            ],
        )

        statement3 = self.env["account.bank.statement"].create(
            {
                "line_ids": [Command.set(line4.ids)],
                "balance_start": -5,
            }
        )
        (statement1 + statement3).flush_recordset(["is_valid"])
        self.assertRecordValues(
            statement1 + statement3,
            [
                {
                    "is_valid": True,
                },
                {
                    "is_valid": False,
                },
            ],
        )

        statement1.balance_end_real = -5
        statement1.flush_recordset(["balance_end_real"])
        (statement1 + statement3).invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1 + statement3,
            [
                {
                    "is_valid": True,
                },
                {
                    "is_valid": True,
                },
            ],
        )
        self.assertRecordValues(
            line1 + line2 + line3 + line4,
            [
                {"date": fields.Date.from_string("2020-01-10"), "statement_id": False},
                {
                    "date": fields.Date.from_string("2020-01-11"),
                    "statement_id": statement1.id,
                },
                {"date": fields.Date.from_string("2020-01-12"), "statement_id": False},
                {
                    "date": fields.Date.from_string("2020-01-13"),
                    "statement_id": statement3.id,
                },
            ],
        )
        self.assertRecordValues(
            statement1 + statement2 + statement3,
            [
                {
                    "is_valid": True,
                    "balance_start": 10,
                    "balance_end_real": -5,
                    "date": fields.Date.from_string("2020-01-11"),
                },
                {
                    "is_valid": True,
                    "balance_start": False,
                    "balance_end_real": 100,
                    "date": False,
                },
                {
                    "is_valid": True,
                    "balance_start": -5,
                    "balance_end_real": -15,
                    "date": fields.Date.from_string("2020-01-13"),
                },
            ],
        )

        line5 = self.create_bank_transaction(-10, "2020-01-13")
        statement4 = self.env["account.bank.statement"].create(
            {
                "line_ids": [Command.set(line5.ids)],
                "balance_start": -15,
            }
        )
        (statement1 + statement4).invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1 + statement4,
            [
                {"is_valid": True},
                {"is_valid": True},
            ],
        )

        line1.statement_id = statement2
        statement2.flush_model()
        (statement1 + statement2).invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1 + statement2, [{"is_valid": False}, {"is_valid": True}]
        )

        statement2.line_ids = line3
        statement2.flush_model()
        (statement1 + statement2 + statement3).invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1 + statement2 + statement3,
            [
                {"is_valid": True},
                {"is_valid": False},
                {"is_valid": False},
            ],
        )

    def test_statement_line_ordering(self):
        self.env.user.company_id = self.company_data_2["company"]

        line7 = self.create_bank_transaction(7, "2020-01-10", sequence=1)
        line8 = self.create_bank_transaction(8, "2020-01-10", sequence=2)
        line2 = self.create_bank_transaction(2, "2020-01-13")
        line6 = self.create_bank_transaction(6, "2020-01-11")
        line5 = self.create_bank_transaction(5, "2020-01-12", sequence=3)
        line4 = self.create_bank_transaction(4, "2020-01-12", sequence=2)
        line1 = self.create_bank_transaction(1, "2020-01-13")
        line3 = self.create_bank_transaction(3, "2020-01-12", sequence=1)

        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": False},
                {"amount": 3, "running_balance": 33, "statement_id": False},
                {"amount": 4, "running_balance": 30, "statement_id": False},
                {"amount": 5, "running_balance": 26, "statement_id": False},
                {"amount": 6, "running_balance": 21, "statement_id": False},
                {"amount": 7, "running_balance": 15, "statement_id": False},
                {"amount": 8, "running_balance": 8, "statement_id": False},
            ],
        )

        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [
                    ("company_id", "=", self.env.company.id),
                    ("amount", ">=", 3),
                    ("amount", "<=", 6),
                ]
            ),
            [
                {"amount": 3, "running_balance": 33},
                {"amount": 4, "running_balance": 30},
                {"amount": 5, "running_balance": 26},
                {"amount": 6, "running_balance": 21},
            ],
        )

        (line2 + line3 + line4).statement_id = statement1 = self.env[
            "account.bank.statement"
        ].create({"balance_start": 20, "balance_end_real": 29})

        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                }
            ],
        )

        statement1.invalidate_recordset(["is_valid"])
        statement1.balance_start = 26
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "balance_end_real": 35,
                }
            ],
        )

        line5.sequence = -1
        statement1.invalidate_recordset(["is_valid"])
        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                }
            ],
        )

        statement1.balance_start = 21
        statement1.invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "balance_end_real": 30,
                }
            ],
        )

        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": statement1.id},
                {"amount": 5, "running_balance": 33, "statement_id": False},
                {"amount": 3, "running_balance": 28, "statement_id": statement1.id},
                {"amount": 4, "running_balance": 25, "statement_id": statement1.id},
                {"amount": 6, "running_balance": 21, "statement_id": False},
                {"amount": 7, "running_balance": 15, "statement_id": False},
                {"amount": 8, "running_balance": 8, "statement_id": False},
            ],
        )

        line8.amount = 18

        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": statement1.id},
                {"amount": 5, "running_balance": 33, "statement_id": False},
                {"amount": 3, "running_balance": 28, "statement_id": statement1.id},
                {"amount": 4, "running_balance": 25, "statement_id": statement1.id},
                {"amount": 6, "running_balance": 31, "statement_id": False},
                {"amount": 7, "running_balance": 25, "statement_id": False},
                {"amount": 18, "running_balance": 18, "statement_id": False},
            ],
        )
        line5.amount = 15

        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 46, "statement_id": False},
                {"amount": 2, "running_balance": 45, "statement_id": statement1.id},
                {"amount": 15, "running_balance": 43, "statement_id": False},
                {"amount": 3, "running_balance": 28, "statement_id": statement1.id},
                {"amount": 4, "running_balance": 25, "statement_id": statement1.id},
                {"amount": 6, "running_balance": 31, "statement_id": False},
                {"amount": 7, "running_balance": 25, "statement_id": False},
                {"amount": 18, "running_balance": 18, "statement_id": False},
            ],
        )

        line7.unlink()

        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 46, "statement_id": False},
                {"amount": 2, "running_balance": 45, "statement_id": statement1.id},
                {"amount": 15, "running_balance": 43, "statement_id": False},
                {"amount": 3, "running_balance": 28, "statement_id": statement1.id},
                {"amount": 4, "running_balance": 25, "statement_id": statement1.id},
                {"amount": 6, "running_balance": 24, "statement_id": False},
                {"amount": 18, "running_balance": 18, "statement_id": False},
            ],
        )
        line1.move_id.action_cancel()
        line6.move_id.action_cancel()
        line6.move_id.action_draft()
        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 45, "statement_id": False},
                {"amount": 2, "running_balance": 45, "statement_id": statement1.id},
                {"amount": 15, "running_balance": 43, "statement_id": False},
                {"amount": 3, "running_balance": 28, "statement_id": statement1.id},
                {"amount": 4, "running_balance": 25, "statement_id": statement1.id},
                {"amount": 6, "running_balance": 18, "statement_id": False},
                {"amount": 18, "running_balance": 18, "statement_id": False},
            ],
        )

        statement1.line_ids = False
        self.env["account.bank.statement.line"].invalidate_model(
            fnames=["running_balance"]
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 42, "statement_id": False},
                {"amount": 2, "running_balance": 42, "statement_id": False},
                {"amount": 15, "running_balance": 40, "statement_id": False},
                {"amount": 3, "running_balance": 25, "statement_id": False},
                {"amount": 4, "running_balance": 22, "statement_id": False},
                {"amount": 6, "running_balance": 18, "statement_id": False},
                {"amount": 18, "running_balance": 18, "statement_id": False},
            ],
        )

    def test_formatted_read_group_running_balance(self):
        self.env.user.company_id = self.company_data_2["company"]
        self.create_bank_transaction(10, "2020-02-01")
        self.create_bank_transaction(20, "2020-02-02")
        self.create_bank_transaction(30, "2020-02-03")

        groups = (
            self.env["account.bank.statement.line"]
            .with_context(show_running_balance_latest=True)
            .formatted_read_group(
                [("company_id", "=", self.env.company.id)],
                ["date:day"],
                ["amount:sum"],
            )
        )
        self.assertEqual(
            sorted(group["running_balance"] for group in groups),
            [10, 30, 60],
        )

    def test_statement_split(self):
        self.env.user.company_id = self.company_data_2["company"]

        line7 = self.create_bank_transaction(7, "2020-01-10", sequence=1)
        line8 = self.create_bank_transaction(8, "2020-01-10", sequence=2)
        line2 = self.create_bank_transaction(2, "2020-01-13")
        line6 = self.create_bank_transaction(6, "2020-01-11")
        _line5 = self.create_bank_transaction(5, "2020-01-12", sequence=3)
        line4 = self.create_bank_transaction(4, "2020-01-12", sequence=2)
        line1 = self.create_bank_transaction(1, "2020-01-13")
        line3 = self.create_bank_transaction(3, "2020-01-12", sequence=1)

        statement1 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line7.id})
            .create({})
        )
        self.assertRecordValues(
            statement1,
            [
                {
                    "balance_start": 0.0,
                    "balance_end": 15.0,
                    "balance_end_real": 15.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        self.assertRecordValues(
            line7 + line8 + line6,
            [
                {"amount": 7, "statement_id": statement1.id},
                {"amount": 8, "statement_id": statement1.id},
                {"amount": 6, "statement_id": False},
            ],
        )

        statement2 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line6.id})
            .create({})
        )
        self.assertRecordValues(
            statement2,
            [
                {
                    "balance_start": 15.0,
                    "balance_end": 21.0,
                    "balance_end_real": 21.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": False},
                {"amount": 3, "running_balance": 33, "statement_id": False},
                {"amount": 4, "running_balance": 30, "statement_id": False},
                {"amount": 5, "running_balance": 26, "statement_id": False},
                {"amount": 6, "running_balance": 21, "statement_id": statement2.id},
                {"amount": 7, "running_balance": 15, "statement_id": statement1.id},
                {"amount": 8, "running_balance": 8, "statement_id": statement1.id},
            ],
        )

        statement1.unlink()
        statement3 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line3.id})
            .create({})
        )
        self.assertRecordValues(
            statement3,
            [
                {
                    "balance_start": 21.0,
                    "balance_end": 33.0,
                    "balance_end_real": 33.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": False},
                {"amount": 3, "running_balance": 33, "statement_id": statement3.id},
                {"amount": 4, "running_balance": 30, "statement_id": statement3.id},
                {"amount": 5, "running_balance": 26, "statement_id": statement3.id},
                {"amount": 6, "running_balance": 21, "statement_id": statement2.id},
                {"amount": 7, "running_balance": 15, "statement_id": False},
                {"amount": 8, "running_balance": 8, "statement_id": False},
            ],
        )
        statement4 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line6.id})
            .create({})
        )
        self.assertRecordValues(
            statement3 + statement4,
            [
                {
                    "balance_start": 21.0,
                    "balance_end": 33.0,
                    "balance_end_real": 33.0,
                    "is_complete": True,
                    "is_valid": True,
                },
                {
                    "balance_start": 0.0,
                    "balance_end": 21.0,
                    "balance_end_real": 21.0,
                    "is_complete": True,
                    "is_valid": True,
                },
            ],
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": False},
                {"amount": 3, "running_balance": 33, "statement_id": statement3.id},
                {"amount": 4, "running_balance": 30, "statement_id": statement3.id},
                {"amount": 5, "running_balance": 26, "statement_id": statement3.id},
                {"amount": 6, "running_balance": 21, "statement_id": statement4.id},
                {"amount": 7, "running_balance": 15, "statement_id": statement4.id},
                {"amount": 8, "running_balance": 8, "statement_id": statement4.id},
            ],
        )
        statement5 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line2.id})
            .create({})
        )
        self.assertRecordValues(
            statement5,
            [
                {
                    "balance_start": 33.0,
                    "balance_end": 35.0,
                    "balance_end_real": 35.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": statement5.id},
                {"amount": 3, "running_balance": 33, "statement_id": statement3.id},
                {"amount": 4, "running_balance": 30, "statement_id": statement3.id},
                {"amount": 5, "running_balance": 26, "statement_id": statement3.id},
                {"amount": 6, "running_balance": 21, "statement_id": statement4.id},
                {"amount": 7, "running_balance": 15, "statement_id": statement4.id},
                {"amount": 8, "running_balance": 8, "statement_id": statement4.id},
            ],
        )
        statement6 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line2.id})
            .create({"reference": "6"})
        )
        self.assertRecordValues(
            statement6,
            [
                {
                    "balance_start": 33.0,
                    "balance_end": 35.0,
                    "balance_end_real": 35.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": statement6.id},
                {"amount": 3, "running_balance": 33, "statement_id": statement3.id},
                {"amount": 4, "running_balance": 30, "statement_id": statement3.id},
                {"amount": 5, "running_balance": 26, "statement_id": statement3.id},
                {"amount": 6, "running_balance": 21, "statement_id": statement4.id},
                {"amount": 7, "running_balance": 15, "statement_id": statement4.id},
                {"amount": 8, "running_balance": 8, "statement_id": statement4.id},
            ],
        )

        statement7 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line4.id})
            .create({})
        )
        self.assertRecordValues(
            statement3 + statement7,
            [
                {
                    "balance_start": 21.0,
                    "balance_end": 24.0,
                    "balance_end_real": 33.0,
                    "is_complete": False,
                    "is_valid": False,
                },
                {
                    "balance_start": 21.0,
                    "balance_end": 30.0,
                    "balance_end_real": 30.0,
                    "is_complete": True,
                    "is_valid": True,
                },
            ],
        )

        statement3._compute_balance_start()
        self.assertRecordValues(
            statement3,
            [
                {
                    "balance_start": 30.0,
                    "balance_end": 33.0,
                    "balance_end_real": 33.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )

        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "running_balance": 36, "statement_id": False},
                {"amount": 2, "running_balance": 35, "statement_id": statement6.id},
                {"amount": 3, "running_balance": 33, "statement_id": statement3.id},
                {"amount": 4, "running_balance": 30, "statement_id": statement7.id},
                {"amount": 5, "running_balance": 26, "statement_id": statement7.id},
                {"amount": 6, "running_balance": 21, "statement_id": statement4.id},
                {"amount": 7, "running_balance": 15, "statement_id": statement4.id},
                {"amount": 8, "running_balance": 8, "statement_id": statement4.id},
            ],
        )

        statement8 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line6.id})
            .create({})
        )
        self.assertRecordValues(
            statement7 + statement8,
            [
                {
                    "balance_end_real": 30.0,
                    "balance_end": 30.0,
                    "balance_start": 21.0,
                    "is_complete": True,
                    "is_valid": True,
                },
                {
                    "balance_end_real": 21.0,
                    "balance_end": 21.0,
                    "balance_start": 0.0,
                    "is_complete": True,
                    "is_valid": True,
                },
            ],
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "statement_id": False},
                {"amount": 2, "statement_id": statement6.id},
                {"amount": 3, "statement_id": statement3.id},
                {"amount": 4, "statement_id": statement7.id},
                {"amount": 5, "statement_id": statement7.id},
                {"amount": 6, "statement_id": statement8.id},
                {"amount": 7, "statement_id": statement8.id},
                {"amount": 8, "statement_id": statement8.id},
            ],
        )

        statement9 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line8.id})
            .create({})
        )
        self.assertRecordValues(
            statement8 + statement9,
            [
                {
                    "balance_end_real": 21.0,
                    "balance_end": 13.0,
                    "balance_start": 0.0,
                    "is_complete": False,
                    "is_valid": False,
                },
                {
                    "balance_end_real": 8.0,
                    "balance_end": 8.0,
                    "balance_start": 0.0,
                    "is_complete": True,
                    "is_valid": True,
                },
            ],
        )

        statement8._compute_balance_start()
        self.assertRecordValues(
            statement8,
            [
                {
                    "balance_end_real": 21.0,
                    "balance_end": 21.0,
                    "balance_start": 8.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )

        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "statement_id": False},
                {"amount": 2, "statement_id": statement6.id},
                {"amount": 3, "statement_id": statement3.id},
                {"amount": 4, "statement_id": statement7.id},
                {"amount": 5, "statement_id": statement7.id},
                {"amount": 6, "statement_id": statement8.id},
                {"amount": 7, "statement_id": statement8.id},
                {"amount": 8, "statement_id": statement9.id},
            ],
        )

        statement10 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line1.id})
            .create({})
        )
        self.assertRecordValues(
            statement10,
            [
                {
                    "balance_start": 35.0,
                    "balance_end": 36.0,
                    "balance_end_real": 36.0,
                    "is_complete": True,
                    "is_valid": True,
                }
            ],
        )
        self.assertRecordValues(
            self.env["account.bank.statement.line"].search(
                [("company_id", "=", self.env.company.id)]
            ),
            [
                {"amount": 1, "statement_id": statement10.id},
                {"amount": 2, "statement_id": statement6.id},
                {"amount": 3, "statement_id": statement3.id},
                {"amount": 4, "statement_id": statement7.id},
                {"amount": 5, "statement_id": statement7.id},
                {"amount": 6, "statement_id": statement8.id},
                {"amount": 7, "statement_id": statement8.id},
                {"amount": 8, "statement_id": statement9.id},
            ],
        )

        all_statements = self.env["account.bank.statement"].search(
            [
                ("line_ids", "!=", False),
                ("company_id", "=", self.env.company.id),
            ]
        )
        all_statements.invalidate_recordset(["is_valid"])
        self.assertRecordValues(
            all_statements,
            [{"is_valid": True, "is_complete": True}] * len(all_statements),
        )

    def test_statement_with_canceled_lines(self):
        line1 = self.create_bank_transaction(
            1, "2020-01-10", journal=self.bank_journal_2
        )
        line2 = self.create_bank_transaction(
            2, "2020-01-11", journal=self.bank_journal_2
        )
        statement1 = self.env["account.bank.statement"].create(
            {
                "line_ids": [Command.set((line1 + line2).ids)],
            }
        )
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "is_valid": True,
                    "date": fields.Date.from_string(line2.date),
                    "balance_start": 0,
                    "balance_end_real": 3,
                }
            ],
        )
        line2.move_id.action_cancel()
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": False,
                    "balance_end": 1,
                    "date": fields.Date.from_string(line1.date),
                }
            ],
        )
        line3 = self.create_bank_transaction(
            2, "2020-01-12", journal=self.bank_journal_2, statement=statement1
        )
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "balance_end": 3,
                    "date": fields.Date.from_string(line3.date),
                }
            ],
        )
        line4 = self.create_bank_transaction(
            4, "2020-01-13", journal=self.bank_journal_2
        )
        line4.move_id.action_cancel()
        line4.move_id.action_draft()
        statement1.line_ids |= line4
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": True,
                    "balance_end": 3,
                    "date": fields.Date.from_string(line3.date),
                }
            ],
        )
        statement2 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": line2.id})
            .create({})
        )
        self.assertRecordValues(
            statement1 + statement2,
            [
                {
                    "is_complete": False,
                    "balance_end": 2,
                    "balance_start": 0,
                    "line_ids": [line4.id, line3.id],
                },
                {
                    "is_complete": True,
                    "balance_start": 0,
                    "balance_end": 1,
                    "line_ids": [line1.id, line2.id],
                },
            ],
        )

        line3.move_id.action_cancel()
        self.assertRecordValues(
            statement1,
            [
                {
                    "is_complete": False,
                    "balance_start": 0,
                    "balance_end": 0,
                }
            ],
        )

        statement3 = self.env["account.bank.statement"].create(
            {
                "line_ids": [Command.set((line3 + line4).ids)],
            }
        )
        self.assertRecordValues(
            statement1 + statement3,
            [
                {
                    "is_complete": False,
                    "balance_start": 0,
                    "balance_end": 0,
                },
                {
                    "is_complete": False,
                    "balance_start": 1,
                    "balance_end": 1,
                },
            ],
        )

    def test_create_statement_line_with_inconsistent_currencies(self):
        statement_line = self.env["account.bank.statement.line"].create(
            {
                "date": "2019-01-01",
                "journal_id": self.bank_journal_1.id,
                "payment_ref": "Happy new year",
                "amount": 200.0,
                "amount_currency": 200.0,
                "foreign_currency_id": self.env.company.currency_id.id,
            }
        )

        self.assertRecordValues(
            statement_line,
            [
                {
                    "currency_id": self.env.company.currency_id.id,
                    "foreign_currency_id": False,
                    "amount": 200.0,
                    "amount_currency": 0.0,
                }
            ],
        )

    def test_statement_balance_warnings(self):
        lines = [
            self.create_bank_transaction(amount, date, journal=self.bank_journal_2)
            for amount, date in [
                (10.0, "2019-01-01"),
                (15.0, "2019-01-02"),
                (20.0, "2019-01-03"),
                (30.0, "2019-01-03"),
                (40.0, "2019-01-04"),
                (50.0, "2019-01-05"),
            ]
        ]

        contexts = [
            {
                "active_ids": [line.id],
                "st_line_id": line.id,
            }
            for line in lines[:3]
        ]

        self.assertRecordValues(
            self.env["account.bank.statement"].with_context(contexts[1]).new({}),
            [
                {
                    "balance_start": 10.0,
                    "balance_end_real": 25.0,
                    "is_valid": True,
                    "is_complete": True,
                }
            ],
        )

        st1 = (
            self.env["account.bank.statement"]
            .with_context(contexts[0])
            .create({"name": "Statement 1"})
        )
        self.assertRecordValues(
            st1,
            [
                {
                    "balance_start": 0.0,
                    "balance_end_real": 10.0,
                    "is_valid": True,
                    "is_complete": True,
                }
            ],
        )
        self.assertEqual(lines[0].statement_id, st1)

        self.assertRecordValues(
            self.env["account.bank.statement"].with_context(contexts[2]).new(),
            [
                {
                    "balance_start": 25.0,
                    "balance_end_real": 45.0,
                    "is_valid": False,
                    "is_complete": True,
                }
            ],
        )

        self.assertRecordValues(
            self.env["account.bank.statement"].with_context(contexts[1]).new(),
            [
                {
                    "balance_start": 10.0,
                    "balance_end_real": 25.0,
                    "is_valid": True,
                    "is_complete": True,
                }
            ],
        )

        context = {
            "active_ids": [line.id for line in lines[:3]],
            "st_line_id": lines[2].id,
        }
        self.assertRecordValues(
            self.env["account.bank.statement"].with_context(context).new({}),
            [
                {
                    "balance_start": 0.0,
                    "balance_end_real": 45.0,
                    "is_valid": True,
                    "is_complete": True,
                    "line_ids": [lines[0].id, lines[1].id, lines[2].id],
                }
            ],
        )

        context = {
            "active_ids": [line.id for line in lines[2:4]],
            "st_line_id": lines[3].id,
        }
        self.assertRecordValues(
            self.env["account.bank.statement"].with_context(context).new({}),
            [
                {
                    "balance_start": 25.0,
                    "balance_end_real": 75.0,
                    "is_valid": False,
                    "is_complete": True,
                    "line_ids": [lines[2].id, lines[3].id],
                }
            ],
        )

        expected_st_vals = [
            {
                "balance_start": 10.0,
                "balance_end_real": 75.0,
                "is_valid": True,
                "is_complete": True,
                "line_ids": [lines[1].id, lines[2].id, lines[3].id],
            }
        ]
        context = {
            "active_ids": [line.id for line in lines[1:4]],
            "st_line_id": lines[3].id,
        }
        self.assertRecordValues(
            self.env["account.bank.statement"].with_context(context).new({}),
            expected_st_vals,
        )

        self.assertRecordValues(
            self.env["account.bank.statement"]
            .with_context({"split_line_id": lines[3].id})
            .new({}),
            expected_st_vals,
        )

        context = {
            "active_ids": [lines[1].id, lines[3].id],
            "st_line_id": lines[3].id,
        }
        with self.assertRaises(UserError):
            self.env["account.bank.statement"].with_context(context).create({})

        st2 = (
            self.env["account.bank.statement"]
            .with_context({"split_line_id": lines[-1].id})
            .create({"name": "Statement 2"})
        )
        self.assertRecordValues(
            st2,
            [
                {
                    "balance_start": 10.0,
                    "balance_end_real": 165.0,
                    "is_valid": True,
                    "is_complete": True,
                }
            ],
        )

        lines[2].move_id.action_cancel()
        context = {
            "active_ids": [lines[1].id, lines[3].id],
            "st_line_id": lines[3].id,
        }
        st3 = (
            self.env["account.bank.statement"]
            .with_context(context)
            .create({"name": "Statement 3"})
        )
        self.assertRecordValues(
            st3,
            [
                {
                    "balance_start": 10.0,
                    "balance_end_real": 55.0,
                    "is_valid": True,
                    "is_complete": True,
                }
            ],
        )

    def test_statement_attachments(self):
        attachment_vals = {
            "datas": base64.b64encode(b"My attachment"),
            "name": "doc.txt",
        }

        attachment = self.env["ir.attachment"].create(attachment_vals)

        statement = self.env["account.bank.statement"].create(
            {
                "name": "test_statement",
                "attachment_ids": [Command.set(attachment.ids)],
            }
        )

        attachment = self.env["ir.attachment"].create(attachment_vals)

        statement.write({"attachment_ids": [Command.link(attachment.id)]})

        self.assertRecordValues(
            statement.attachment_ids,
            [
                {"res_id": statement.id, "res_model": "account.bank.statement"},
                {"res_id": statement.id, "res_model": "account.bank.statement"},
            ],
        )

    def test_statement_reverse_keeps_partner(self):
        partner = self.env["res.partner"].create(
            {
                "name": "Test Partner",
            }
        )

        statement_line = self.env["account.bank.statement.line"].create(
            {
                "date": "2019-01-01",
                "payment_ref": "line_1",
                "partner_id": partner.id,
                "journal_id": self.bank_journal_1.id,
                "amount": 1250.0,
            }
        )
        move = statement_line.move_id

        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=move.ids)
            .create(
                {
                    "date": fields.Date.from_string("2021-02-01"),
                    "journal_id": self.bank_journal_1.id,
                }
            )
        )
        reversal = move_reversal.reverse_moves()
        reversed_move = self.env["account.move"].browse(reversal["res_id"])

        self.assertEqual(reversed_move.partner_id, partner)

    def test_bank_transaction_creation_with_default_journal_entry_date(self):
        invoice_date_field = self.env["ir.model.fields"].search(
            [("model", "=", "account.move"), ("name", "=", "invoice_date")], limit=1
        )
        self.env["ir.default"].create(
            {
                "field_id": invoice_date_field.id,
                "json_value": '"2023-10-16"',
            }
        )

        transaction = self.create_bank_transaction(
            1, "2020-01-10", journal=self.bank_journal_1
        )
        assert (
            transaction.date
            == transaction.move_id.date
            == fields.Date.from_string("2020-01-10")
        )
