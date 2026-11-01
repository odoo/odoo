# -*- coding: utf-8 -*-
from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestHrExpenseReimburse(TransactionCase):
    """Employee reimbursement must produce a real payment that clears the
    employee payable account (not just a stamped date)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_account = cls.env["account.account"].create({
            "name": "Reimburse Expense",
            "code": "519901",
            "account_type": "expense",
        })
        cls.cash_account = cls.env["account.account"].create({
            "name": "Reimburse Cash",
            "code": "119901",
            "account_type": "asset_cash",
        })
        cls.journal = cls.env["account.journal"].create({
            "name": "Reimburse Cash",
            "type": "cash",
            "code": "RMB",
            "default_account_id": cls.cash_account.id,
        })
        cls.partner = cls.env["res.partner"].create({
            "name": "Reimburse Employee Contact",
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Reimburse Employee",
            "work_contact_id": cls.partner.id,
        })
        cls.product = cls.env["product.product"].create({
            "name": "Reimburse Product",
            "type": "service",
        })

    def _create_posted_expense(self, amount=1000.0):
        """Create an employee-paid expense and its posted receipt entry."""
        expense = self.env["hr.expense"].create({
            "name": "Reimburse Expense",
            "product_id": self.product.id,
            "total_amount": amount,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
        })
        payable = self.partner.with_company(
            self.env.company).property_account_payable_id
        move = self.env["account.move"].create({
            "journal_id": self.journal.id,
            "date": fields.Date.context_today(self.env.user),
            "line_ids": [
                (0, 0, {
                    "name": "Expense",
                    "account_id": self.expense_account.id,
                    "partner_id": self.partner.id,
                    "debit": amount,
                    "credit": 0.0,
                }),
                (0, 0, {
                    "name": "Expense",
                    "account_id": payable.id,
                    "partner_id": self.partner.id,
                    "debit": 0.0,
                    "credit": amount,
                }),
            ],
        })
        move.action_post()
        expense.account_move_id = move.id
        expense.reimbursement_date = fields.Date.context_today(self.env.user)
        return expense

    def test_reimbursement_creates_payment_and_clears_payable(self):
        expense = self._create_posted_expense(1000.0)
        payable = self.partner.with_company(
            self.env.company).property_account_payable_id

        expense.action_mark_reimbursed()

        payment = expense.od19_reimbursement_payment_id
        self.assertTrue(payment)
        self.assertEqual(payment.payment_type, "outbound")
        self.assertEqual(payment.partner_type, "supplier")
        self.assertEqual(payment.partner_id, self.partner)
        self.assertEqual(payment.amount, 1000.0)
        self.assertIn(payment.state, ("in_process", "paid"))
        self.assertEqual(
            expense.reimbursement_date,
            fields.Date.context_today(self.env.user),
        )

        payable_lines = self.env["account.move.line"].search([
            ("account_id", "=", payable.id),
            ("partner_id", "=", self.partner.id),
        ])
        self.assertEqual(len(payable_lines), 2)
        self.assertTrue(all(payable_lines.mapped("reconciled")))
        self.assertEqual(len(payable_lines.mapped("full_reconcile_id")), 1)
        self.assertEqual(sum(payable_lines.mapped("amount_residual")), 0.0)

    def test_reimbursement_twice_raises(self):
        expense = self._create_posted_expense(500.0)
        expense.action_mark_reimbursed()
        with self.assertRaises(UserError):
            expense.action_mark_reimbursed()

    def test_reimbursement_without_posting_raises(self):
        expense = self.env["hr.expense"].create({
            "name": "Not posted",
            "product_id": self.product.id,
            "total_amount": 100.0,
            "employee_id": self.employee.id,
            "payment_mode": "own_account",
        })
        with self.assertRaises(UserError):
            expense.action_mark_reimbursed()

    def test_reimbursement_company_account_raises(self):
        expense = self.env["hr.expense"].create({
            "name": "Company paid",
            "product_id": self.product.id,
            "total_amount": 100.0,
            "employee_id": self.employee.id,
            "payment_mode": "company_account",
        })
        with self.assertRaises(UserError):
            expense.action_mark_reimbursed()
