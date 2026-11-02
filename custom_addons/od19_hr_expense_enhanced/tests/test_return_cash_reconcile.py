# -*- coding: utf-8 -*-
from odoo import fields
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestReturnCashReconcile(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_account = cls.env["account.account"].create({
            "name": "Test Expense",
            "code": "519900",
            "account_type": "expense",
        })
        cls.cash_account = cls.env["account.account"].create({
            "name": "Test Cash",
            "code": "119900",
            "account_type": "asset_cash",
        })
        cls.cash_journal = cls.env["account.journal"].create({
            "name": "Return Cash",
            "type": "cash",
            "code": "RCH",
            "default_account_id": cls.cash_account.id,
        })
        cls.partner = cls.env["res.partner"].create({"name": "Employee Contact"})
        cls.employee = cls.env["hr.employee"].create({
            "name": "Test Employee",
            "work_contact_id": cls.partner.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Expense Product",
            "type": "service",
        })

    def _create_expense(self, amount):
        expense = self.env["hr.expense"].create({
            "name": "Test Expense",
            "product_id": self.product.id,
            "total_amount": amount,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
        })
        expense.od19_cash_state = "received"
        return expense

    def _create_advance_move(self, amount):
        """Record the cash advance given to the employee (Dr payable / Cr cash)."""
        move = self.env["account.move"].create({
            "journal_id": self.cash_journal.id,
            "date": fields.Date.context_today(self.env.user),
            "line_ids": [
                (0, 0, {
                    "name": "Cash advance",
                    "account_id": self.partner.property_account_payable_id.id,
                    "partner_id": self.partner.id,
                    "debit": amount,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "name": "Cash advance",
                    "account_id": self.cash_account.id,
                    "debit": 0.0,
                    "credit": amount,
                }),
            ],
        })
        move.action_post()
        return move

    def test_return_cash_reconciles_employee_payable(self):
        expense = self._create_expense(5000.0)
        self._create_advance_move(5000.0)

        wizard = self.env["od19.expense.return.cash"].create({
            "expense_id": expense.id,
            "amount": 5000.0,
            "return_date": fields.Date.context_today(self.env.user),
            "journal_id": self.cash_journal.id,
            "create_accounting_entry": True,
        })
        wizard.action_return_cash()

        self.assertEqual(expense.od19_cash_state, "returned")
        payable_lines = self.env["account.move.line"].search([
            ("account_id", "=", self.partner.property_account_payable_id.id),
            ("partner_id", "=", self.partner.id),
        ])
        self.assertEqual(len(payable_lines), 2)
        self.assertTrue(all(payable_lines.mapped("reconciled")))
        self.assertEqual(len(payable_lines.mapped("full_reconcile_id")), 1)
