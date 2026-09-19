from dateutil.relativedelta import relativedelta
from freezegun import freeze_time

from odoo import Command
from odoo.tests import tagged
from odoo.tools.misc import format_amount

from odoo.addons.account.tests.test_account_journal_dashboard_common import (
    TestAccountJournalDashboardCommon,
)


@tagged("post_install", "-at_install")
class TestAccountJournalDashboard(TestAccountJournalDashboardCommon):
    @freeze_time("2019-01-22")
    def test_customer_invoice_dashboard(self):
        if (
            self.env["ir.module.module"]
            .search([("name", "=", "account_3way_match")])
            .state
            == "installed"
        ):
            self.skipTest("This test won't work if account_3way_match is installed")

        journal = self.company_data["default_journal_sale"]

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "journal_id": journal.id,
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-21",
                "date": "2019-01-21",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "quantity": 40.0,
                            "name": "product test 1",
                            "discount": 10.00,
                            "price_unit": 2.27,
                            "tax_ids": [],
                        },
                    )
                ],
            }
        )
        refund = self.env["account.move"].create(
            {
                "move_type": "out_refund",
                "journal_id": journal.id,
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-21",
                "date": "2019-01-21",
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1.0,
                            "name": "product test 1",
                            "price_unit": 13.3,
                            "tax_ids": [],
                        },
                    )
                ],
            }
        )

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]

        self.assertEqual(dashboard_data["number_draft"], 2)
        self.assertIn("68.42", dashboard_data["sum_draft"])

        self.assertEqual(dashboard_data["number_waiting"], 0)
        self.assertIn("0.00", dashboard_data["sum_waiting"])

        invoice.action_post()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data["number_draft"], 1)
        self.assertIn(
            "-\N{ZERO WIDTH NO-BREAK SPACE}13.30", dashboard_data["sum_draft"]
        )

        self.assertEqual(dashboard_data["number_waiting"], 1)
        self.assertIn("81.72", dashboard_data["sum_waiting"])

        partial_payment = self.env["account.payment"].create(
            {
                "amount": 13.3,
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
            }
        )
        partial_payment.action_post()

        (invoice + partial_payment.move_id).line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
        ).reconcile()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data["number_draft"], 1)
        self.assertIn("13.3", dashboard_data["sum_draft"])

        self.assertEqual(dashboard_data["number_waiting"], 1)
        self.assertIn("68.42", dashboard_data["sum_waiting"])

        refund.action_post()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data["number_draft"], 0)
        self.assertIn("0.00", dashboard_data["sum_draft"])

        self.assertEqual(dashboard_data["number_waiting"], 2)
        self.assertIn("55.12", dashboard_data["sum_waiting"])

        payment = self.env["account.payment"].create(
            {
                "amount": 10.0,
                "payment_type": "outbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
            }
        )
        payment.action_post()

        (refund + payment.move_id).line_ids.filtered(
            lambda line: line.account_type == "asset_receivable"
        ).reconcile()

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data["number_draft"], 0)
        self.assertIn("0.00", dashboard_data["sum_draft"])

        self.assertEqual(dashboard_data["number_waiting"], 2)
        self.assertIn("65.12", dashboard_data["sum_waiting"])

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(dashboard_data["number_late"], 2)
        self.assertIn("65.12", dashboard_data["sum_late"])

    def test_sale_purchase_journal_for_purchase(self):
        if (
            self.env["ir.module.module"]
            .search([("name", "=", "account_3way_match")])
            .state
            == "installed"
        ):
            self.skipTest("This test won't work if account_3way_match is installed")

        foreign_currency = self.other_currency
        company_currency = self.company_data["currency"]

        setup_values = [
            [self.company_data["default_journal_purchase"], foreign_currency],
            [
                self.company_data["default_journal_purchase"].copy(
                    {
                        "currency_id": foreign_currency.id,
                        "default_account_id": self.company_data[
                            "default_account_expense"
                        ].id,
                    }
                ),
                foreign_currency,
            ],
            [
                self.company_data["default_journal_purchase"].copy(
                    {
                        "currency_id": foreign_currency.id,
                        "default_account_id": self.company_data[
                            "default_account_expense"
                        ].id,
                    }
                ),
                company_currency,
            ],
            [
                self.company_data["default_journal_purchase"].copy(
                    {
                        "currency_id": company_currency.id,
                        "default_account_id": self.company_data[
                            "default_account_expense"
                        ].id,
                    }
                ),
                company_currency,
            ],
            [
                self.company_data["default_journal_purchase"].copy(
                    {
                        "currency_id": company_currency.id,
                        "default_account_id": self.company_data[
                            "default_account_expense"
                        ].id,
                    }
                ),
                foreign_currency,
            ],
        ]

        expected_vals_list = [
            [1, 100, 1, 55, 1, 55, company_currency],
            [1, 200, 1, 110, 1, 110, foreign_currency],
            [1, 400, 1, 220, 1, 220, foreign_currency],
            [1, 200, 1, 110, 1, 110, company_currency],
            [1, 100, 1, 55, 1, 55, company_currency],
        ]

        for (purchase_journal, bill_currency), expected_vals in zip(
            setup_values, expected_vals_list, strict=True
        ):
            with self.subTest(
                purchase_journal_currency=purchase_journal.currency_id,
                bill_currency=bill_currency,
                expected_vals=expected_vals,
            ):
                bill = self.init_invoice(
                    "in_invoice",
                    invoice_date="2017-01-01",
                    post=True,
                    amounts=[200],
                    currency=bill_currency,
                    journal=purchase_journal,
                )
                _draft_bill = self.init_invoice(
                    "in_invoice",
                    invoice_date="2017-01-01",
                    post=False,
                    amounts=[200],
                    currency=bill_currency,
                    journal=purchase_journal,
                )

                payment = self.init_payment(
                    -90, post=True, date="2017-01-01", currency=bill_currency
                )
                (bill + payment.move_id).line_ids.filtered_domain(
                    [
                        (
                            "account_id",
                            "=",
                            self.company_data["default_account_payable"].id,
                        )
                    ]
                ).reconcile()

                self.assertDashboardPurchaseSaleData(purchase_journal, *expected_vals)

    def test_sale_purchase_journal_for_multi_currency_sale(self):
        if (
            self.env["ir.module.module"]
            .search([("name", "=", "account_3way_match")])
            .state
            == "installed"
        ):
            self.skipTest("This test won't work if account_3way_match is installed")

        currency = self.other_currency
        company_currency = self.company_data["currency"]

        invoice = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "invoice_date": "2017-01-01",
                "date": "2017-01-01",
                "partner_id": self.partner_a.id,
                "currency_id": currency.id,
                "invoice_line_ids": [(0, 0, {"name": "test", "price_unit": 200})],
            }
        )
        invoice.action_post()

        payment = self.env["account.payment"].create(
            {
                "amount": 90.0,
                "date": "2016-01-01",
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "currency_id": currency.id,
            }
        )
        payment.action_post()

        (invoice + payment.move_id).line_ids.filtered_domain(
            [("account_id", "=", self.company_data["default_account_receivable"].id)]
        ).reconcile()

        default_journal_sale = self.company_data["default_journal_sale"]
        dashboard_data = default_journal_sale._get_journal_dashboard_data_batched()[
            default_journal_sale.id
        ]
        self.assertEqual(
            format_amount(self.env, 55, company_currency), dashboard_data["sum_waiting"]
        )
        self.assertEqual(
            format_amount(self.env, 55, company_currency), dashboard_data["sum_late"]
        )

    @freeze_time("2023-03-15")
    def test_purchase_journal_numbers_and_sums(self):
        if (
            self.env["ir.module.module"]
            .search([("name", "=", "account_3way_match")])
            .state
            == "installed"
        ):
            self.skipTest("This test won't work if account_3way_match is installed")

        company_currency = self.company_data["currency"]
        journal = self.company_data["default_journal_purchase"]

        self._create_test_vendor_bills(journal)
        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(3, dashboard_data["number_waiting"])
        self.assertEqual(
            format_amount(self.env, 4440, company_currency),
            dashboard_data["sum_waiting"],
        )
        self.assertEqual(1, dashboard_data["number_late"])
        self.assertEqual(
            format_amount(self.env, 40, company_currency), dashboard_data["sum_late"]
        )

    def test_gap_in_sequence_warning(self):
        journal = self.company_data["default_journal_sale"]
        self.assertFalse(journal._query_has_sequence_holes())
        moves = (
            self.env["account.move"]
            .create(
                [
                    {
                        "move_type": "out_invoice",
                        "journal_id": journal.id,
                        "partner_id": self.partner_a.id,
                        "invoice_date": f"1900-01-{i + 1:02d}",
                        "date": f"2019-01-{i + 1:02d}",
                        "invoice_line_ids": [
                            Command.create(
                                {
                                    "product_id": self.product_a.id,
                                    "quantity": 40.0,
                                    "name": "product test 1",
                                    "price_unit": 2.27,
                                    "tax_ids": [],
                                }
                            )
                        ],
                    }
                    for i in range(10)
                ]
            )
            .sorted("date")
        )
        gap_date = moves[3].date

        moves[:8].action_post()
        self.assertFalse(journal._query_has_sequence_holes())

        moves[2:4].action_draft()
        self.assertTrue(journal._query_has_sequence_holes())
        moves[3].unlink()
        self.assertTrue(journal._query_has_sequence_holes())

        moves[2].action_post()
        self.company_data["company"].account_config_id.write(
            {"fiscalyear_lock_date": gap_date + relativedelta(days=1)}
        )
        self.assertFalse(journal._query_has_sequence_holes())

        moves[6].action_draft()
        moves[6].action_cancel()
        self.assertTrue(journal._query_has_sequence_holes())

    def test_bank_journal_with_default_account_as_outstanding_account_payments(self):
        bank_journal = self.company_data["default_journal_bank"].copy()
        bank_journal.outbound_payment_channel_ids[
            0
        ].payment_account_id = bank_journal.default_account_id
        bank_journal.inbound_payment_channel_ids[
            0
        ].payment_account_id = bank_journal.default_account_id
        payment = self.env["account.payment"].create(
            {
                "amount": 100,
                "payment_type": "inbound",
                "partner_type": "customer",
                "journal_id": bank_journal.id,
            }
        )
        payment.action_post()

        dashboard_data = bank_journal._get_journal_dashboard_data_batched()[
            bank_journal.id
        ]
        self.assertEqual(dashboard_data["nb_misc_operations"], 0)
        self.assertEqual(
            dashboard_data["account_balance"],
            (bank_journal.currency_id or self.env.company.currency_id).format(100),
        )

    def test_outstanding_payments_count_is_per_payment_not_per_currency(self):
        bank_journal = self.company_data["default_journal_bank"]
        for amount in (10.0, 20.0, 30.0):
            payment = self.env["account.payment"].create(
                {
                    "amount": amount,
                    "payment_type": "inbound",
                    "partner_type": "customer",
                    "journal_id": bank_journal.id,
                }
            )
            payment.action_post()

        dashboard_data = bank_journal._get_journal_dashboard_data_batched()[
            bank_journal.id
        ]
        self.assertEqual(
            dashboard_data["nb_lines_outstanding_pay_account_balance"],
            3,
            "3 same-currency outstanding payments must be counted as 3, not 1.",
        )

    def test_bank_journal_different_currency(self):
        foreign_currency = self.other_currency
        bank_journal = self.company_data["default_journal_bank"].copy(
            {"currency_id": foreign_currency.id}
        )

        self.assertNotEqual(
            bank_journal.currency_id, bank_journal.company_id.currency_id
        )

        move = self.env["account.move"].create(
            {
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": bank_journal.default_account_id.id,
                            "currency_id": foreign_currency.id,
                            "amount_currency": 100,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "currency_id": foreign_currency.id,
                            "amount_currency": -100,
                        }
                    ),
                ],
            }
        )
        move.action_post()

        dashboard_data = bank_journal._get_journal_dashboard_data_batched()[
            bank_journal.id
        ]
        self.assertEqual(
            dashboard_data.get("misc_operations_balance", 0),
            foreign_currency.format(100),
        )

        bank_journal.default_account_id.currency_id = False
        company_currency_move = self.env["account.move"].create(
            {
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "account_id": bank_journal.default_account_id.id,
                            "debit": 100,
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_assets"
                            ].id,
                            "credit": 100,
                        }
                    ),
                ],
            }
        )
        company_currency_move.action_post()
        dashboard_data = bank_journal._get_journal_dashboard_data_batched()[
            bank_journal.id
        ]

        self.assertEqual(dashboard_data.get("misc_operations_balance", 0), None)
        self.assertEqual(dashboard_data.get("misc_class", ""), "text-warning")

    def test_to_check_posted(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Test Foreign Currency Journal",
                "type": "sale",
                "code": "TEST",
                "currency_id": self.currency.id,
                "company_id": self.env.company.id,
            }
        )
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "journal_id": journal.id,
                "partner_id": self.partner_a.id,
                "checked": False,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "product_id": self.product_a.id,
                            "quantity": 1,
                            "price_unit": 100,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(
            dashboard_data["to_check_balance"], journal.currency_id.format(0)
        )

        move.action_post()
        move.checked = False

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(
            dashboard_data["to_check_balance"], journal.currency_id.format(100)
        )

    def test_to_check_amount_different_currency(self):
        self.env.ref("base.CHF").write({"active": True})
        self.env["res.currency.rate"].create(
            {
                "currency_id": self.env.ref("base.EUR").id,
                "name": "2024-12-01",
                "rate": 2.0,
            }
        )
        self.env["res.currency.rate"].create(
            {
                "currency_id": self.env.ref("base.CHF").id,
                "name": "2024-12-01",
                "rate": 4.0,
            }
        )
        journal = self.env["account.journal"].create(
            {
                "name": "Test Foreign Currency Journal",
                "type": "sale",
                "code": "TEST",
                "currency_id": self.env.ref("base.EUR").id,
                "company_id": self.env.company.id,
            }
        )
        moves = self.env["account.move"].create(
            [
                {
                    "move_type": "out_invoice",
                    "journal_id": journal.id,
                    "partner_id": self.partner_a.id,
                    "currency_id": currency.id,
                    "checked": False,
                    "invoice_line_ids": [
                        Command.create(
                            {
                                "product_id": self.product_a.id,
                                "quantity": 1,
                                "price_unit": 100,
                                "tax_ids": [],
                            }
                        )
                    ],
                }
                for currency in (self.env.ref("base.EUR"), self.env.ref("base.CHF"))
            ]
        )
        moves.action_post()
        moves.checked = False

        dashboard_data = journal._get_journal_dashboard_data_batched()[journal.id]
        self.assertEqual(
            dashboard_data["to_check_balance"], journal.currency_id.format(150)
        )

    @freeze_time("2023-06-15")
    def test_misc_operations_shared_default_account_windows(self):
        windowed = self.company_data["default_journal_bank"]
        shared_account = windowed.default_account_id
        open_journal = windowed.copy({"name": "Shared-Account Bank", "code": "SHBNK"})
        open_journal.default_account_id = shared_account
        self.assertEqual(open_journal.default_account_id, shared_account)

        self.env["account.bank.statement"].create(
            {
                "name": "Seed statement",
                "line_ids": [
                    Command.create(
                        {
                            "journal_id": windowed.id,
                            "date": "2023-05-01",
                            "payment_ref": "seed",
                            "amount": 10.0,
                        }
                    )
                ],
            }
        )
        self.assertEqual(windowed.last_statement_id.date.isoformat(), "2023-05-01")
        self.assertFalse(open_journal.last_statement_id)

        self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.company_data["default_journal_misc"].id,
                "date": "2023-03-15",
                "line_ids": [
                    Command.create(
                        {
                            "account_id": shared_account.id,
                            "debit": 100.0,
                            "credit": 0.0,
                            "name": "misc on shared account",
                        }
                    ),
                    Command.create(
                        {
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                            "debit": 0.0,
                            "credit": 100.0,
                            "name": "counterpart",
                        }
                    ),
                ],
            }
        ).action_post()

        data = (windowed | open_journal)._get_journal_dashboard_data_batched()
        self.assertEqual(data[windowed.id]["nb_misc_operations"], 0)
        self.assertEqual(data[open_journal.id]["nb_misc_operations"], 1)


@tagged("post_install", "-at_install")
class TestAccountJournalDashboardSigns(TestAccountJournalDashboardCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.par_currency = cls.setup_other_currency("GBP", rates=[("1900-01-01", 1.0)])

    def _journal_in(self, jtype, code, currency):
        return self.env["account.journal"].create(
            {
                "name": code,
                "code": code,
                "type": jtype,
                "company_id": self.env.company.id,
                "currency_id": currency.id if currency else False,
            }
        )

    def _post(self, journal, move_type, amount, currency):
        account = self.company_data[
            "default_account_revenue"
            if move_type.startswith("out")
            else "default_account_expense"
        ]
        move = self.env["account.move"].create(
            {
                "move_type": move_type,
                "journal_id": journal.id,
                "partner_id": self.partner_a.id,
                "currency_id": currency.id,
                "invoice_date": "2019-01-01",
                "date": "2019-01-01",
                "invoice_date_due": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "l",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": account.id,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        move.action_post()
        return move

    def _sums(self, journal):
        data = journal._get_journal_dashboard_data_batched()[journal.id]
        return data["sum_waiting"], data["sum_late"]

    @freeze_time("2019-06-01")
    def test_credit_note_subtracts_in_a_foreign_currency_journal(self):
        expected = format_amount(self.env, 700, self.par_currency)

        journal = self._journal_in("sale", "FXS1", self.par_currency)
        self._post(journal, "out_invoice", 1000, self.par_currency)
        self._post(journal, "out_refund", 300, self.par_currency)
        self.assertEqual(self._sums(journal), (expected, expected))

    @freeze_time("2019-06-01")
    def test_credit_note_agrees_across_both_currency_branches(self):
        company_currency = self.company_data["currency"]
        control = self._journal_in("sale", "FXS2", None)
        self._post(control, "out_invoice", 1000, company_currency)
        self._post(control, "out_refund", 300, company_currency)

        foreign = self._journal_in("sale", "FXS3", self.par_currency)
        self._post(foreign, "out_invoice", 1000, self.par_currency)
        self._post(foreign, "out_refund", 300, self.par_currency)

        _waiting, control_late = self._sums(control)
        _waiting, foreign_late = self._sums(foreign)
        self.assertEqual(control_late, format_amount(self.env, 700, company_currency))
        self.assertEqual(foreign_late, format_amount(self.env, 700, self.par_currency))

    @freeze_time("2019-06-01")
    def test_vendor_receipt_adds_in_a_foreign_currency_journal(self):
        expected = format_amount(self.env, 1400, self.par_currency)

        journal = self._journal_in("purchase", "FXP1", self.par_currency)
        self._post(journal, "in_invoice", 1000, self.par_currency)
        self._post(journal, "in_receipt", 400, self.par_currency)
        self.assertEqual(self._sums(journal), (expected, expected))

    @freeze_time("2019-06-01")
    def test_every_invoice_type_keeps_its_residual_sign(self):
        cases = [
            ("sale", "out_invoice", 100),
            ("sale", "out_refund", -100),
            ("sale", "out_receipt", 100),
            ("purchase", "in_invoice", -100),
            ("purchase", "in_refund", 100),
            ("purchase", "in_receipt", -100),
        ]
        for index, (jtype, move_type, signed) in enumerate(cases):
            with self.subTest(move_type=move_type):
                journal = self._journal_in(jtype, f"FX{index}", self.par_currency)
                self._post(journal, move_type, 100, self.par_currency)
                display = signed if jtype == "sale" else -signed
                self.assertEqual(
                    self._sums(journal)[1],
                    format_amount(self.env, display, self.par_currency),
                )

    def test_the_negative_residual_set_is_the_outbound_set(self):
        self.assertEqual(
            sorted(self.env["account.move"].get_outbound_types()),
            ["in_invoice", "in_receipt", "out_refund"],
        )


@tagged("post_install", "-at_install")
class TestAccountJournalToCheckValue(TestAccountJournalDashboardCommon):
    def setUp(self):
        super().setUp()
        self.journal = self.env["account.journal"].create(
            {
                "name": "TCV",
                "code": "TCV",
                "type": "sale",
                "company_id": self.env.company.id,
            }
        )

    def _post_unreviewed(self, amount):
        move = self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "journal_id": self.journal.id,
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "l",
                            "quantity": 1,
                            "price_unit": amount,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )
        move.action_post()
        move.checked = False
        return move

    def _to_check(self):
        self.journal.invalidate_recordset()
        data = self.journal._get_journal_dashboard_data_batched()[self.journal.id]
        return data["number_to_check"], data["to_check_balance"]

    def _pay_in_full(self, move):
        payment = self.env["account.payment"].create(
            {
                "journal_id": self.company_data["default_journal_bank"].id,
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.partner_a.id,
                "amount": move.amount_total,
                "currency_id": move.currency_id.id,
                "date": "2019-01-02",
            }
        )
        payment.action_post()
        (move + payment.move_id).line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_receivable"
        ).reconcile()
        move.checked = False

    def test_a_paid_but_unreviewed_invoice_still_has_a_value(self):
        currency = self.company_data["currency"]
        unpaid = self._post_unreviewed(500)
        paid = self._post_unreviewed(800)
        self._pay_in_full(paid)

        self.assertEqual(paid.payment_state, "paid")
        self.assertEqual(paid.amount_residual, 0.0)
        self.assertEqual(unpaid.amount_total + paid.amount_total, 1300)
        self.assertEqual(self._to_check(), (2, format_amount(self.env, 1300, currency)))

    def test_a_misc_entry_in_a_sale_journal_carries_its_total(self):
        currency = self.company_data["currency"]
        self._post_unreviewed(500)
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.journal.id,
                "date": "2019-01-01",
                "line_ids": [
                    Command.create(
                        {
                            "name": "d",
                            "debit": 70,
                            "credit": 0,
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "c",
                            "debit": 0,
                            "credit": 70,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )
        entry.action_post()
        entry.checked = False

        self.assertEqual(entry.amount_residual_signed, 0.0)
        self.assertEqual(self._to_check(), (2, format_amount(self.env, 570, currency)))


@tagged("post_install", "-at_install")
class TestAccountJournalEntryPresence(TestAccountJournalDashboardCommon):
    def _journal(self, code):
        return self.env["account.journal"].create(
            {
                "name": code,
                "code": code,
                "type": "sale",
                "company_id": self.env.company.id,
            }
        )

    def _invoice(self, journal):
        return self.env["account.move"].create(
            {
                "move_type": "out_invoice",
                "journal_id": journal.id,
                "partner_id": self.partner_a.id,
                "invoice_date": "2019-01-01",
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "l",
                            "quantity": 1,
                            "price_unit": 100,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "tax_ids": [],
                        }
                    )
                ],
            }
        )

    def test_entry_presence_distinguishes_draft_from_posted(self):
        empty, drafted, posted = (self._journal(c) for c in ("EP1", "EP2", "EP3"))
        self._invoice(drafted)
        self._invoice(posted).action_post()

        (empty + drafted + posted).invalidate_recordset()
        self.assertEqual(
            [(j.has_entries, j.has_posted_entries) for j in (empty, drafted, posted)],
            [(False, False), (True, False), (True, True)],
        )

    def test_entry_presence_on_an_empty_recordset(self):
        self.assertEqual(self.env["account.journal"].browse().mapped("has_entries"), [])
