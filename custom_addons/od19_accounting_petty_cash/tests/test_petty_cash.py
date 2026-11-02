from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPettyCash(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.petty_cash_account = cls.env["account.account"].create(
            {
                "name": "Petty Cash",
                "code": "111002",
                "account_type": "asset_cash",
            }
        )
        cls.expense_account = cls.env["account.account"].create(
            {
                "name": "Office Expense",
                "code": "511002",
                "account_type": "expense",
            }
        )
        cls.cash_account = cls.env["account.account"].create(
            {
                "name": "Cash",
                "code": "111001",
                "account_type": "asset_cash",
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Petty Cash Journal",
                "type": "general",
                "code": "PC",
                "default_account_id": cls.cash_account.id,
            }
        )

    def test_create_petty_cash_fund(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 10000.0,
            }
        )
        self.assertEqual(fund.balance, 10000.0)
        self.assertEqual(fund.state, "active")

    def test_create_petty_cash_transaction_expense(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 10000.0,
            }
        )
        transaction = self.env["petty.cash.transaction"].create(
            {
                "fund_id": fund.id,
                "name": "Office supplies",
                "amount": 500.0,
                "transaction_type": "expense",
                "expense_account_id": self.expense_account.id,
                "date": "2024-01-15",
            }
        )
        self.assertEqual(transaction.state, "draft")
        self.assertEqual(fund.balance, 10000.0)

    def test_post_petty_cash_expense(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 10000.0,
            }
        )
        transaction = self.env["petty.cash.transaction"].create(
            {
                "fund_id": fund.id,
                "name": "Office supplies",
                "amount": 500.0,
                "transaction_type": "expense",
                "expense_account_id": self.expense_account.id,
                "date": "2024-01-15",
                "journal_id": self.journal.id,
            }
        )
        transaction.action_post()
        self.assertEqual(transaction.state, "posted")
        self.assertEqual(fund.balance, 9500.0)

    def test_post_petty_cash_replenishment(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 10000.0,
            }
        )
        transaction = self.env["petty.cash.transaction"].create(
            {
                "fund_id": fund.id,
                "name": "Replenishment",
                "amount": 2000.0,
                "transaction_type": "replenishment",
                "date": "2024-01-15",
                "journal_id": self.journal.id,
            }
        )
        transaction.action_post()
        self.assertEqual(transaction.state, "posted")
        self.assertEqual(fund.balance, 12000.0)

    def test_petty_cash_expense_requires_expense_account(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 10000.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["petty.cash.transaction"].create(
                {
                    "fund_id": fund.id,
                    "name": "Office supplies",
                    "amount": 500.0,
                    "transaction_type": "expense",
                    "date": "2024-01-15",
                }
            )

    def test_petty_cash_amount_must_be_positive(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 10000.0,
            }
        )
        with self.assertRaises(ValidationError):
            self.env["petty.cash.transaction"].create(
                {
                    "fund_id": fund.id,
                    "name": "Test",
                    "amount": -100.0,
                    "transaction_type": "expense",
                    "expense_account_id": self.expense_account.id,
                    "date": "2024-01-15",
                }
            )

    def test_cannot_expense_more_than_balance(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 1000.0,
            }
        )
        transaction = self.env["petty.cash.transaction"].create(
            {
                "fund_id": fund.id,
                "name": "Big expense",
                "amount": 2000.0,
                "transaction_type": "expense",
                "expense_account_id": self.expense_account.id,
                "date": "2024-01-15",
                "journal_id": self.journal.id,
            }
        )
        with self.assertRaises(ValidationError):
            transaction.action_post()

    def test_action_reconcile_matches_fund_account_lines(self):
        fund = self.env["petty.cash.fund"].create(
            {
                "name": "Office Petty Cash",
                "account_id": self.petty_cash_account.id,
                "amount": 10000.0,
            }
        )
        expense = self.env["petty.cash.transaction"].create(
            {
                "fund_id": fund.id,
                "name": "Office supplies",
                "amount": 500.0,
                "transaction_type": "expense",
                "expense_account_id": self.expense_account.id,
                "date": "2024-01-15",
                "journal_id": self.journal.id,
            }
        )
        expense.action_post()
        replenishment = self.env["petty.cash.transaction"].create(
            {
                "fund_id": fund.id,
                "name": "Replenishment",
                "amount": 500.0,
                "transaction_type": "replenishment",
                "date": "2024-01-16",
                "journal_id": self.journal.id,
            }
        )
        replenishment.action_post()

        expense.action_reconcile()

        fund_lines = self.env["account.move.line"].search(
            [("account_id", "=", self.petty_cash_account.id)]
        )
        self.assertEqual(len(fund_lines), 2)
        self.assertTrue(all(fund_lines.mapped("reconciled")))
        self.assertEqual(len(fund_lines.mapped("full_reconcile_id")), 1)
