from freezegun import freeze_time

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged

from .common_report_engine import TestAccountReportsCommon


@tagged("post_install", "-at_install")
class TestMultiCurrenciesRevaluationReport(TestAccountReportsCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.other_currency_2 = cls.setup_other_currency(
            "XAF", rates=[("2016-01-01", 10.0), ("2017-01-01", 20.0)]
        )

        cls.expense_account_1 = cls.company_data["default_account_expense"]
        cls.expense_account_2 = cls.copy_account(
            cls.company_data["default_account_expense"]
        )

        cls.env["res.currency.rate"].create(
            {
                "name": "2023-01-20",
                "rate": 1,
                "currency_id": cls.other_currency.id,
                "company_id": cls.company_data["company"].id,
            }
        )

        cls.env["res.currency.rate"].create(
            {
                "name": "2023-01-25",
                "rate": 2,
                "currency_id": cls.other_currency.id,
                "company_id": cls.company_data["company"].id,
            }
        )

        cls.env["res.currency.rate"].create(
            {
                "name": "2023-01-30",
                "rate": 4,
                "currency_id": cls.other_currency.id,
                "company_id": cls.company_data["company"].id,
            }
        )

        cls.env["res.currency.rate"].create(
            {
                "name": "2023-01-20",
                "rate": 1,
                "currency_id": cls.other_currency_2.id,
                "company_id": cls.company_data["company"].id,
            }
        )

        cls.report = cls.env.ref("account.multicurrency_revaluation_report")

    @classmethod
    def pay_move(
        cls,
        move,
        amount,
        date,
        account_type="liability_payable",
        currency=None,
        partner_type=None,
    ):
        if not currency:
            currency = move.currency_id

        assert amount
        if amount > 0:
            payment_type = "outbound"
            payment_method = "account.account_payment_method_manual_out"
            partner_type = partner_type or "supplier"
        else:
            payment_type = "inbound"
            payment_method = "account.account_payment_method_manual_in"
            partner_type = partner_type or "customer"

        payment = cls.env["account.payment"].create(
            {
                "payment_type": payment_type,
                "amount": abs(amount),
                "currency_id": currency.id,
                "journal_id": cls.company_data["default_journal_bank"].id,
                "date": fields.Date.from_string(date),
                "partner_id": move.partner_id.id,
                "payment_method_id": cls.env.ref(payment_method).id,
                "partner_type": partner_type,
            }
        )
        payment.action_post()
        lines_to_reconcile = move.line_ids.filtered(
            lambda x: x.account_type == account_type
        )
        lines_to_reconcile += payment.move_id.line_ids.filtered(
            lambda x: x.account_type == account_type
        )
        lines_to_reconcile.reconcile()

    @classmethod
    def create_move_one_line(
        cls,
        move_type,
        journal_id,
        partner_id,
        date,
        invoice_date,
        currency_id,
        account_id,
        quantity,
        price_unit,
        payment_term_id=None,
    ):
        move = cls.env["account.move"].create(
            {
                "move_type": move_type,
                "partner_id": partner_id,
                "date": date,
                "invoice_date": invoice_date,
                "journal_id": journal_id,
                "currency_id": currency_id,
                "invoice_payment_term_id": payment_term_id,
                "invoice_line_ids": [
                    Command.create(
                        {
                            "name": "My Super Product",
                            "account_id": account_id,
                            "quantity": quantity,
                            "price_unit": price_unit,
                            "tax_ids": [Command.clear()],
                            "currency_id": cls.other_currency.id,
                        }
                    ),
                ],
            }
        )
        move.action_post()
        return move

    def test_multi_currencies(self):
        """Two moves in the same currency (CAD), the first one paid by 3 payments in
        3 different currencies (CAD, XAF, USD).
        """
        first_bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=800.0,
        )

        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=200.0,
        )

        self.pay_move(
            first_bill,
            400,
            "2023-01-21",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.other_currency,
        )

        self.pay_move(
            first_bill,
            250,
            "2023-01-21",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.other_currency_2,
        )

        self.pay_move(
            first_bill,
            150,
            "2023-01-21",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.company_data["currency"],
        )

        # Test the report in 2023.
        options = self._generate_options(self.report, "2023-01-01", "2023-12-31")
        options["unfold_all"] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -200.0, -200.0, -50.0, 150.0),
                ("211000 Account Payable", -200.0, -200.0, -50.0, 150.0),
                ("BILL/2023/01/0002", -200.0, -200.0, -50.0, 150.0),
                ("Total 211000 Account Payable", -200.0, -200.0, -50.0, 150.0),
                ("Total CAD", -200.0, -200.0, -50.0, 150.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_same_currency(self):
        """Two moves in the same currency, the first bill reconciled with a bank statement line.
        The statement line and the move share the same currency (CAD).
        """
        first_bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=800.0,
        )

        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=200.0,
        )

        bank_statement = (
            self.env["account.bank.statement.line"]
            .with_context(auto_statement_processing=False)
            .create(
                {
                    "journal_id": self.company_data["default_journal_bank"].id,
                    "payment_ref": "payment_move_line",
                    "partner_id": self.partner_a.id,
                    "foreign_currency_id": self.other_currency.id,
                    "amount": -400,
                    "amount_currency": -800,
                    "date": "2023-01-21",
                }
            )
        )

        bank_statement.set_line_bank_statement_line(
            first_bill.line_ids.filtered(
                lambda line: line.account_type == "liability_payable"
            ).id
        )

        # Test the report in 2023.
        options = self._generate_options(self.report, "2023-01-01", "2023-12-31")
        options["unfold_all"] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -200.0, -200.0, -50.0, 150.0),
                ("211000 Account Payable", -200.0, -200.0, -50.0, 150.0),
                ("BILL/2023/01/0002", -200.0, -200.0, -50.0, 150.0),
                ("Total 211000 Account Payable", -200.0, -200.0, -50.0, 150.0),
                ("Total CAD", -200.0, -200.0, -50.0, 150.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_exclude_account_for_adjustment_entry(self):
        """Check the exclude functionality of the report.

        A bill partially reconciled with a bank statement line still shows up in the report,
        as does an unpaid invoice; excluding the remainder of the bill removes it.
        """

        first_bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-01",
            invoice_date="2023-01-01",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=800.0,
        )

        # Invoice
        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="out_invoice",
            journal_id=self.company_data["default_journal_sale"].id,
            date="2023-01-01",
            invoice_date="2023-01-01",
            currency_id=self.other_currency.id,
            account_id=self.copy_account(
                self.company_data["default_account_revenue"]
            ).id,
            quantity=1,
            price_unit=100.0,
        )

        bank_statement = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.company_data["default_journal_bank"].id,
                "payment_ref": "payment_move_line",
                "partner_id": self.partner_a.id,
                "foreign_currency_id": self.other_currency.id,
                "amount": -300,
                "amount_currency": -600,
                "date": "2023-01-01",
            }
        )

        bank_statement.set_line_bank_statement_line(
            first_bill.line_ids.filtered(
                lambda account: account.account_type == "liability_payable"
            ).id
        )

        # Test the report in 2023.
        options = self._generate_options(self.report, "2023-01-01", "2023-12-31")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -100.0, -50.0, -25.0, 25.0),
                ("121000 Account Receivable", 100.0, 50.0, 25.0, -25.0),
                ("INV/2023/00001", 100.0, 50.0, 25.0, -25.0),
                ("Total 121000 Account Receivable", 100.0, 50.0, 25.0, -25.0),
                ("211000 Account Payable", -200.0, -100.0, -50.0, 50.0),
                ("BILL/2023/01/0001", -200.0, -100.0, -50.0, 50.0),
                ("Total 211000 Account Payable", -200.0, -100.0, -50.0, 50.0),
                ("Total CAD", -100.0, -50.0, -25.0, 25.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        oldest_line_id = self.report._get_generic_line_id(
            "report.formula.line",
            self.env.ref("account.multicurrency_revaluation_to_adjust").id,
        )
        old_line_id = self.report._get_generic_line_id(
            "res.currency",
            self.other_currency.id,
            markup={"groupby": "currency_id"},
            parent_line_id=oldest_line_id,
        )
        line_id = self.report._get_generic_line_id(
            "account.account",
            first_bill.line_ids.account_id.filtered(
                lambda account: account.account_type == "liability_payable"
            ).id,
            markup={"groupby": "account_id"},
            parent_line_id=old_line_id,
        )

        self.env[
            "account.multicurrency.revaluation.report.handler"
        ].action_multi_currency_revaluation_toggle_provision(
            options, {"line_id": line_id}
        )
        options["unfold_all"] = True

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", 100.0, 50.0, 25.0, -25.0),
                ("121000 Account Receivable", 100.0, 50.0, 25.0, -25.0),
                ("INV/2023/00001", 100.0, 50.0, 25.0, -25.0),
                ("Total 121000 Account Receivable", 100.0, 50.0, 25.0, -25.0),
                ("Total CAD", 100.0, 50.0, 25.0, -25.0),
                ("Excluded Accounts", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -200.0, -100.0, -50.0, 50.0),
                ("211000 Account Payable", -200.0, -100.0, -50.0, 50.0),
                ("BILL/2023/01/0001", -200.0, -100.0, -50.0, 50.0),
                ("Total 211000 Account Payable", -200.0, -100.0, -50.0, 50.0),
                ("Total CAD", -200.0, -100.0, -50.0, 50.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_same_rate(self):
        """Make sure no adjustment lines are generated if the rate is unchanged
        (i.e. do not create 0 balance adjustment lines)
        """
        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, "2023-01-21", "2023-01-21")
        options["unfold_all"] = True

        # Check the CAD lines: the rate is unchanged, so the adjustment is 0.
        self.assertLinesValues(
            # pylint: disable = C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 1.0 CAD)", -1000.0, -1000.0, -1000.0, 0.0),
                ("211000 Account Payable", -1000.0, -1000.0, -1000.0, 0.0),
                ("BILL/2023/01/0001", -1000.0, -1000.0, -1000.0, 0.0),
                ("Total 211000 Account Payable", -1000.0, -1000.0, -1000.0, 0.0),
                ("Total CAD", -1000.0, -1000.0, -1000.0, 0.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        with self.assertRaises(UserError, msg="No adjustment should be needed"):
            env = self.env(
                context={
                    **self.env.context,
                    "multicurrency_revaluation_report_options": {
                        **options,
                        "unfold_all": False,
                    },
                }
            )
            env["account.multicurrency.revaluation.wizard"].create(
                {
                    "journal_id": self.company_data["default_journal_misc"].id,
                    "expense_provision_account_id": self.company_data[
                        "default_account_expense"
                    ].id,
                    "income_provision_account_id": self.company_data[
                        "default_account_revenue"
                    ].id,
                }
            )

    def test_changing_rate_between_move_and_payment(self):
        """The currency rate changes between the creation of a move and its payment.

        Covers several payments for the same move, each at a different date and rate.
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-26")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 2.0 CAD)", -1000.0, -1000.0, -500.0, 500.0),
                ("211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("BILL/2023/01/0001", -1000.0, -1000.0, -500.0, 500.0),
                ("Total 211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("Total CAD", -1000.0, -1000.0, -500.0, 500.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        # First payment for the bill at the given date to check if it appears in the report when changing the date_to
        self.pay_move(
            bill,
            500,
            "2023-01-26",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.other_currency,
        )

        # Second payment at a later date to fully paid the bill
        self.pay_move(
            bill,
            500,
            "2023-02-01",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.other_currency,
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-31")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -500.0, -500.0, -125.0, 375.0),
                ("211000 Account Payable", -500.0, -500.0, -125.0, 375.0),
                ("BILL/2023/01/0001", -500.0, -500.0, -125.0, 375.0),
                ("Total 211000 Account Payable", -500.0, -500.0, -125.0, 375.0),
                ("Total CAD", -500.0, -500.0, -125.0, 375.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    @freeze_time("2023-01-26")
    def test_payment_in_company_currency_invoice_in_foreign_currency_fully_reconcile(
        self,
    ):
        """A move in a foreign currency paid in the company currency; the rate change makes it
        fully reconciled, so nothing is left to display in the report.
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        # We pay the bill for 500 but thanks to the changing of the rate (1 --> 2), 500 become 1000 and the move is
        # fully reconciled, so we don't need to display anything on the report
        self.pay_move(
            bill,
            500,
            "2023-01-26",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.company_data["currency"],
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-02-20")
        self.assertEqual(len(self.report._get_lines(options)), 0)

    @freeze_time("2023-01-26")
    def test_payment_in_company_currency_invoice_in_foreign_currency_not_fully_reconcile(
        self,
    ):
        """A move in a foreign currency partially paid in the company currency."""
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        # We pay the first part of the bill, thanks to the changing of rates we have paid 600
        self.pay_move(
            bill,
            300,
            "2023-01-26",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.company_data["currency"],
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-26")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 2.0 CAD)", -400.0, -400.0, -200.0, 200.0),
                ("211000 Account Payable", -400.0, -400.0, -200.0, 200.0),
                ("BILL/2023/01/0001", -400.0, -400.0, -200.0, 200.0),
                ("Total 211000 Account Payable", -400.0, -400.0, -200.0, 200.0),
                ("Total CAD", -400.0, -400.0, -200.0, 200.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        # We check the report again with other date to witness the new changing of rates
        options = self._generate_options(self.report, "2023-01-01", "2023-02-01")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -400.0, -400.0, -100.0, 300.0),
                ("211000 Account Payable", -400.0, -400.0, -100.0, 300.0),
                ("BILL/2023/01/0001", -400.0, -400.0, -100.0, 300.0),
                ("Total 211000 Account Payable", -400.0, -400.0, -100.0, 300.0),
                ("Total CAD", -400.0, -400.0, -100.0, 300.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    @freeze_time("2023-01-28")
    def test_pay_all_move_check_before_full_payment(self):
        """Fully pay the move, then check that the report still displays its lines
        when opened at a date before the payment.
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        # We fully pay the bill, in company currency
        self.pay_move(
            bill,
            1000,
            "2023-01-28",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.company_data["currency"],
        )

        # The report shouldn't display anything after the full payment.
        options = self._generate_options(self.report, "2023-01-01", "2023-01-29")
        options["unfold_all"] = True
        self.assertEqual(len(self.report._get_lines(options)), 0)

        # The report should display the bill before the full payment.
        options = self._generate_options(self.report, "2023-01-01", "2023-01-26")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 2.0 CAD)", -1000.0, -1000.0, -500.0, 500.0),
                ("211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("BILL/2023/01/0001", -1000.0, -1000.0, -500.0, 500.0),
                ("Total 211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("Total CAD", -1000.0, -1000.0, -500.0, 500.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    @freeze_time("2023-01-26")
    def test_move_credit_note(self):
        """Create a credit note, change the currency rate and then the payment. Check if the report gives the correct
        values before and after the payment
        """
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-30")
        options["unfold_all"] = True
        self.assertEqual(len(self.report._get_lines(options)), 6)

        self.pay_move(
            bill,
            1000,
            "2023-01-26",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.company_data["currency"],
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-30")
        options["unfold_all"] = True

        self.assertEqual(len(self.report._get_lines(options)), 0)

        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=bill.ids)
            .create({"journal_id": bill.journal_id.id, "date": "2023-01-26"})
        )
        reversal = move_reversal.reverse_moves()
        self.env["account.move"].browse(reversal["res_id"]).action_post()

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                                               Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", 1000.0, 500.0, 250.0, -250.0),
                ("211000 Account Payable", 1000.0, 500.0, 250.0, -250.0),
                (
                    "RBILL/2023/01/0001 (Reversal of: BILL/2023/01/0001)",
                    1000.0,
                    500.0,
                    250.0,
                    -250.0,
                ),
                ("Total 211000 Account Payable", 1000.0, 500.0, 250.0, -250.0),
                ("Total CAD", 1000.0, 500.0, 250.0, -250.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    @freeze_time("2023-01-26")
    def test_with_payment_term(self):
        """Payment term requiring 30% up front and the rest within 60 days.

        Check the report before and after the payment.
        """
        account_payment_term_advance_60days = self.env["account.payment.term"].create(
            {
                "name": "account_payment_term_advance_60days",
                "company_id": self.company_data["company"].id,
                "line_ids": [
                    Command.create(
                        {
                            "value_amount": 30,
                            "value": "percent",
                            "nb_days": 0,
                        }
                    ),
                    Command.create(
                        {
                            "value_amount": 70,
                            "value": "percent",
                            "nb_days": 60,
                        }
                    ),
                ],
            }
        )

        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
            payment_term_id=account_payment_term_advance_60days.id,
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-30")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -1000.0, -1000.0, -250.0, 750.0),
                ("211000 Account Payable", -1000.0, -1000.0, -250.0, 750.0),
                ("BILL/2023/01/0001 installment #1", -300.0, -300.0, -75.0, 225.0),
                ("BILL/2023/01/0001 installment #2", -700.0, -700.0, -175.0, 525.0),
                ("Total 211000 Account Payable", -1000.0, -1000.0, -250.0, 750.0),
                ("Total CAD", -1000.0, -1000.0, -250.0, 750.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        # The price is double since the rate is x2 So the amount of the payment is 300
        self.pay_move(
            bill,
            150,
            "2023-01-26",
            account_type=self.company_data["default_account_payable"].account_type,
            currency=self.company_data["currency"],
        )

        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -700.0, -700.0, -175.0, 525.0),
                ("211000 Account Payable", -700.0, -700.0, -175.0, 525.0),
                ("BILL/2023/01/0001 installment #2", -700.0, -700.0, -175.0, 525.0),
                ("Total 211000 Account Payable", -700.0, -700.0, -175.0, 525.0),
                ("Total CAD", -700.0, -700.0, -175.0, 525.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        # We check when coming back before the payment the lines are ok
        options = self._generate_options(self.report, "2023-01-01", "2023-01-25")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 2.0 CAD)", -1000.0, -1000.0, -500.0, 500.0),
                ("211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("BILL/2023/01/0001 installment #1", -300.0, -300.0, -150.0, 150.0),
                ("BILL/2023/01/0001 installment #2", -700.0, -700.0, -350.0, 350.0),
                ("Total 211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("Total CAD", -1000.0, -1000.0, -500.0, 500.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_transfer_invoice_to_another_partner(self):
        """The bill amount is still found in the report once the payable is moved to another partner."""
        bill = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.company_data["default_journal_misc"].id,
                "date": "2023-01-22",
                "line_ids": [
                    Command.create(
                        {
                            "partner_id": self.partner_a.id,
                            "currency_id": self.other_currency.id,
                            "amount_currency": 1000.0,
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                        }
                    ),
                    Command.create(
                        {
                            "partner_id": self.partner_b.id,
                            "currency_id": self.other_currency.id,
                            "amount_currency": -1000.0,
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                        }
                    ),
                ],
            }
        )
        entry.action_post()

        lines_to_reconcile = entry.line_ids.filtered(
            lambda line: (
                line.partner_id == self.partner_a
                and line.account_type
                == self.company_data["default_account_payable"].account_type
            )
        )
        lines_to_reconcile += bill.line_ids.filtered(
            lambda line: (
                line.account_type
                == self.company_data["default_account_payable"].account_type
            )
        )
        lines_to_reconcile.reconcile()

        options = self._generate_options(self.report, "2023-01-01", "2023-01-31")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -1000.0, -1000.0, -250.0, 750.0),
                ("211000 Account Payable", -1000.0, -1000.0, -250.0, 750.0),
                ("MISC/2023/01/0001", -1000.0, -1000.0, -250.0, 750.0),
                ("Total 211000 Account Payable", -1000.0, -1000.0, -250.0, 750.0),
                ("Total CAD", -1000.0, -1000.0, -250.0, 750.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    @freeze_time("2023-01-26")
    def test_refund_invoice_keep_exchange_diff_line(self):
        """Create an invoice, cancel it with a credit note.
        Check the report, unreconcile the credit note and
        check the report again.
        """
        # Create a customer invoice with a rate of 1 USD = 1 CAD
        invoice = self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="out_invoice",
            journal_id=self.company_data["default_journal_sale"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_revenue"].id,
            quantity=1,
            price_unit=1000.0,
        )

        # Reverse the customer invoice with a rate of 1 USD = 2 CAD to create a partial credit note
        move_reversal = (
            self.env["account.move.reversal"]
            .with_context(active_model="account.move", active_ids=invoice.ids)
            .create(
                {
                    "journal_id": invoice.journal_id.id,
                    "date": "2023-01-26",
                }
            )
        )
        reversal = move_reversal.reverse_moves()
        credit_note = self.env["account.move"].browse(reversal["res_id"])
        credit_note.invoice_line_ids[0].price_unit = 300  # Only reverse for 300
        credit_note.action_post()
        line_to_reconciles = (invoice + credit_note).line_ids.filtered(
            lambda l: (
                l.account_type
                == self.company_data["default_account_receivable"].account_type
            )
        )

        #  Checking the report after reconciliation between the invoice and the credit note (Rate 1 USD = 4 CAD)
        options = self._generate_options(self.report, "2023-01-01", "2023-01-30")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", 700.0, 700.0, 175.0, -525.0),
                ("121000 Account Receivable", 700.0, 700.0, 175.0, -525.0),
                ("INV/2023/00001", 700.0, 700.0, 175.0, -525.0),
                ("Total 121000 Account Receivable", 700.0, 700.0, 175.0, -525.0),
                ("Total CAD", 700.0, 700.0, 175.0, -525.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        # Delete the reconciliation
        partial = self.env["account.partial.reconcile"].search(
            [
                ("debit_move_id", "=", line_to_reconciles[0].id),
                ("credit_move_id", "=", line_to_reconciles[1].id),
            ]
        )
        partial.unlink()

        # Check the report in february, the exchange diff should disappear as it was computed in january (Rate 1 USD = 4 CAD)
        options = self._generate_options(self.report, "2023-01-01", "2023-02-15")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                                           Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", 700.0, 850.0, 175.0, -675.0),
                ("121000 Account Receivable", 700.0, 850.0, 175.0, -675.0),
                (
                    "RINV/2023/00001 (Reversal of: INV/2023/00001)",
                    -300.0,
                    -150.0,
                    -75.0,
                    75.0,
                ),
                ("INV/2023/00001", 1000.0, 1000.0, 250.0, -750.0),
                ("Total 121000 Account Receivable", 700.0, 850.0, 175.0, -675.0),
                ("Total CAD", 700.0, 850.0, 175.0, -675.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_invoice_with_different_rate_than_the_existing_one(self):
        """A rate customized on a single entry (by editing its debit/credit and amount_currency)
        is kept: the report uses it for the balance in foreign currency and at operation rate.
        """
        # Special rate of 3
        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2023-01-21",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "expense line",
                            "debit": 300.0,
                            "credit": 0.0,
                            "currency_id": self.other_currency.id,
                            "amount_currency": 900,
                            "account_id": self.company_data[
                                "default_account_expense"
                            ].id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "payable line",
                            "partner_id": self.partner_a.id,
                            "currency_id": self.other_currency.id,
                            "debit": 0.0,
                            "credit": 300.0,
                            "amount_currency": -900.0,
                            "account_id": self.company_data[
                                "default_account_payable"
                            ].id,
                        }
                    ),
                ],
            }
        )
        entry.action_post()

        # Opening the report for a rate at 4 instead of 3
        options = self._generate_options(self.report, "2023-01-01", "2023-01-31")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", -900.0, -300.0, -225.0, 75.0),
                ("211000 Account Payable", -900.0, -300.0, -225.0, 75.0),
                ("MISC/2023/01/0001 payable line", -900.0, -300.0, -225.0, 75.0),
                ("Total 211000 Account Payable", -900.0, -300.0, -225.0, 75.0),
                ("Total CAD", -900.0, -300.0, -225.0, 75.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_current_liability_reco_bank_journal_aml(self):
        """An entry on a reconcilable current liability account in a foreign currency, reconciled
        with a bank journal aml.

        Before reconciliation the bank journal aml must not impact the report, its amount being
        already realized; once reconciled with the current liability aml, it must.
        """
        special_liability_current_account = self.env["account.account"].create(
            {
                "name": "201 GOL",
                "code": "201",
                "account_type": "liability_current",
                "reconcile": True,
                "currency_id": self.other_currency.id,
            }
        )
        self.company_data["default_journal_bank"].currency_id = self.other_currency.id

        entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2023-01-21",
                "journal_id": self.company_data["default_journal_misc"].id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "liability line",
                            "debit": 50.0,
                            "credit": 0.0,
                            "currency_id": self.other_currency.id,
                            "amount_currency": 100.0,
                            "account_id": special_liability_current_account.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "revenue line",
                            "currency_id": self.other_currency.id,
                            "debit": 0.0,
                            "credit": 50.0,
                            "amount_currency": -100.0,
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                        }
                    ),
                ],
            }
        )
        entry.action_post()

        self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.company_data["default_journal_bank"].id,
                "payment_ref": "payment_move_line",
                "foreign_currency_id": self.other_currency.id,
                "amount": -10.0,
                "amount_currency": -30.0,
                "date": "2023-01-23",
            }
        )

        bank_entry = self.env["account.move"].create(
            {
                "move_type": "entry",
                "date": "2023-01-23",
                "journal_id": self.company_data["default_journal_bank"].id,
                "line_ids": [
                    Command.create(
                        {
                            "name": "liability line",
                            "debit": 0.0,
                            "credit": 10.0,
                            "currency_id": self.other_currency.id,
                            "amount_currency": -30.0,
                            "account_id": special_liability_current_account.id,
                        }
                    ),
                    Command.create(
                        {
                            "name": "revenue line",
                            "currency_id": self.other_currency.id,
                            "debit": 10.0,
                            "credit": 0.0,
                            "amount_currency": 30.0,
                            "account_id": self.company_data[
                                "default_journal_bank"
                            ].default_account_id.id,
                        }
                    ),
                ],
            }
        )
        bank_entry.action_post()

        # Checking the report before reconciliation
        options = self._generate_options(self.report, "2023-01-01", "2023-01-31")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", 90.0, 40.0, 22.5, -17.5),
                ("101401 Bank", 20.0, 0.0, 5.0, 5.0),
                ("BNK1/2023/00002 revenue line", 30.0, 10.0, 7.5, -2.5),
                ("BNK1/2023/00001 payment_move_line", -10.0, -10.0, -2.5, 7.5),
                ("Total 101401 Bank", 20.0, 0.0, 5.0, 5.0),
                ("201 201 GOL", 70.0, 40.0, 17.5, -22.5),
                ("BNK1/2023/00002 liability line", -30.0, -10.0, -7.5, 2.5),
                ("MISC/2023/01/0001 liability line", 100.0, 50.0, 25.0, -25.0),
                ("Total 201 201 GOL", 70.0, 40.0, 17.5, -22.5),
                ("Total CAD", 90.0, 40.0, 22.5, -17.5),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

        line_to_reconciles = (entry + bank_entry).line_ids.filtered(
            lambda l: l.account_type == special_liability_current_account.account_type
        )
        line_to_reconciles.reconcile()

        # After reconciliation, the bank journal aml should impact the report
        options = self._generate_options(self.report, "2023-01-01", "2023-01-31")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 4.0 CAD)", 90.0, 35.0, 22.5, -12.5),
                ("101401 Bank", 20.0, 0.0, 5.0, 5.0),
                ("BNK1/2023/00002 revenue line", 30.0, 10.0, 7.5, -2.5),
                ("BNK1/2023/00001 payment_move_line", -10.0, -10.0, -2.5, 7.5),
                ("Total 101401 Bank", 20.0, 0.0, 5.0, 5.0),
                ("201 201 GOL", 70.0, 35.0, 17.5, -17.5),
                ("MISC/2023/01/0001 liability line", 70.0, 35.0, 17.5, -17.5),
                ("Total 201 201 GOL", 70.0, 35.0, 17.5, -17.5),
                ("Total CAD", 90.0, 35.0, 22.5, -12.5),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_no_pl_account_present(self):
        """An account with a currency on it is NOT present in the report when it is a p&l account."""

        self.company_data[
            "default_account_expense"
        ].currency_id = self.other_currency.id
        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="in_invoice",
            journal_id=self.company_data["default_journal_purchase"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_expense"].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-26")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 2.0 CAD)", -1000.0, -1000.0, -500.0, 500.0),
                ("211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("BILL/2023/01/0001", -1000.0, -1000.0, -500.0, 500.0),
                ("Total 211000 Account Payable", -1000.0, -1000.0, -500.0, 500.0),
                ("Total CAD", -1000.0, -1000.0, -500.0, 500.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )

    def test_adjustment_entry_with_tax_on_expense_account(self):
        """Make sure the adjustment entry is correctly generated even when
        the expense account has default taxes.
        """
        self.create_move_one_line(
            partner_id=self.partner_a.id,
            move_type="out_invoice",
            journal_id=self.company_data["default_journal_sale"].id,
            date="2023-01-21",
            invoice_date="2023-01-21",
            currency_id=self.other_currency.id,
            account_id=self.company_data["default_account_revenue"].id,
            quantity=1,
            price_unit=1000.0,
        )

        options = self._generate_options(self.report, "2023-01-01", "2023-01-26")
        options["unfold_all"] = True
        self.assertLinesValues(
            # pylint: disable=C0326
            self.report._get_lines(options),
            #   Name                       Balance in foreign currency     Balance at op. rate     Balance at curr rate     Adjustment
            [0, 1, 2, 3, 4],
            [
                ("Accounts To Adjust", "", "", "", ""),
                ("CAD (1 USD = 2.0 CAD)", 1000.0, 1000.0, 500.0, -500.0),
                ("121000 Account Receivable", 1000.0, 1000.0, 500.0, -500.0),
                ("INV/2023/00001", 1000.0, 1000.0, 500.0, -500.0),
                ("Total 121000 Account Receivable", 1000.0, 1000.0, 500.0, -500.0),
                ("Total CAD", 1000.0, 1000.0, 500.0, -500.0),
            ],
            options,
            currency_map={
                1: {"currency": self.other_currency},
            },
        )
        expense_account = self.company_data["default_account_expense"]
        expense_account.tax_ids = [self.company_data["default_tax_purchase"].id]
        env = self.env(
            context={
                **self.env.context,
                "multicurrency_revaluation_report_options": {
                    **options,
                    "unfold_all": False,
                },
            }
        )
        wizard = env["account.multicurrency.revaluation.wizard"].create(
            {
                "journal_id": self.company_data["default_journal_misc"].id,
                "expense_provision_account_id": expense_account.id,
                "income_provision_account_id": self.company_data[
                    "default_account_revenue"
                ].id,
            }
        )
        entry_data = wizard.create_entries()
        entry = self.env["account.move"].browse(entry_data["res_id"])

        self.assertRecordValues(
            entry.invoice_line_ids,
            [
                {
                    "name": "Provision for CAD (1 USD = 2.0 CAD)",
                    "debit": 0.00,
                    "credit": 500.0,
                },
                {
                    "name": "Expense Provision for CAD",
                    "debit": 500.00,
                    "credit": 0.0,
                },
            ],
        )
