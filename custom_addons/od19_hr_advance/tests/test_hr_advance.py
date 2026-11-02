# -*- coding: utf-8 -*-
"""Tests for the employee cash advance workflow (od19_hr_advance).

Covered flow
------------
draft -> submit (2-tier approval) -> approved -> paid -> cleared

The employee receivable (``advance_account_id``) must reach zero once the
advance is cleared, which is the acceptance criterion of Wave 6 / WS-03.
"""

from odoo import Command, fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import new_test_user

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestHrAdvance(AccountTestInvoicingCommon):

    @classmethod
    def get_default_groups(cls):
        # ``AccountTestInvoicingCommon`` runs the class with an independent
        # accounting user that has no HR groups. The advance flow must create
        # ``hr.employee`` (which needs ``resource.resource`` create rights) and
        # ``hr.expense`` records, so extend the default groups accordingly.
        return (
            super().get_default_groups()
            | cls.env.ref("hr.group_hr_user")
            | cls.env.ref("hr_expense.group_hr_expense_user")
        )

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # --- Approvers ---------------------------------------------------
        cls.supervisor = new_test_user(
            cls.env,
            login="od19_adv_supervisor",
            name="Advance Supervisor",
            groups="base.group_user,hr_expense.group_hr_expense_manager",
        )
        cls.accountant = new_test_user(
            cls.env,
            login="od19_adv_accountant",
            name="Advance Accountant",
            groups="base.group_user,account.group_account_manager",
        )

        # --- Accounts ----------------------------------------------------
        cls.advance_account = cls.copy_account(
            cls.company_data["default_account_receivable"],
            {"name": "Employee Advance (Test)", "reconcile": True},
        )
        cls.expense_account = cls.copy_account(
            cls.company_data["default_account_expense"],
            {"name": "Advance Expense (Test)"},
        )

        # --- Employee ----------------------------------------------------
        cls.employee_partner = cls.env["res.partner"].create({
            "name": "Advance Employee Contact",
        })
        cls.employee = cls.env["hr.employee"].create({
            "name": "Advance Employee",
            "work_contact_id": cls.employee_partner.id,
        })

        # --- Expense product used when clearing --------------------------
        cls.expense_product = cls.env["product.product"].create({
            "name": "Advance Expense Product",
            "type": "service",
            "property_account_expense_id": cls.expense_account.id,
        })

        cls.bank_journal = cls.company_data["default_journal_bank"]

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_advance(self, amount=10000.0):
        return self.env["od19.hr.advance"].create({
            "employee_id": self.employee.id,
            "date": fields.Date.context_today(self.env.user),
            "amount": amount,
            "advance_account_id": self.advance_account.id,
            "journal_id": self.bank_journal.id,
            "company_id": self.env.company.id,
        })

    def _approve_advance(self, advance):
        """Submit and clear both approval tiers, then approve the advance."""
        advance.action_confirm()
        advance.with_user(self.supervisor).validate_tier()
        advance.invalidate_recordset()
        advance.with_user(self.accountant).validate_tier()
        advance.invalidate_recordset()
        advance.action_confirm()
        return advance

    def _create_paid_advance(self, amount=10000.0):
        advance = self._create_advance(amount)
        self._approve_advance(advance)
        advance.action_pay()
        advance.invalidate_recordset()
        return advance

    def _create_expense(self, amount):
        return self.env["hr.expense"].create({
            "name": "Advance Clearing Expense",
            "employee_id": self.employee.id,
            "product_id": self.expense_product.id,
            "total_amount": amount,
            "payment_mode": "own_account",
            "company_id": self.env.company.id,
        })

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    def test_tier_definition_model_names_include_hr_advance(self):
        names = self.env["tier.definition"]._get_tier_validation_model_names()
        self.assertIn("od19.hr.advance", names)

    def test_two_tier_definitions_registered(self):
        definitions = self.env["tier.definition"].search([
            ("model", "=", "od19.hr.advance"),
        ])
        self.assertEqual(len(definitions), 2)

    # ------------------------------------------------------------------
    # Approval workflow
    # ------------------------------------------------------------------
    def test_draft_advance_needs_validation(self):
        advance = self._create_advance()
        self.assertTrue(advance.name)
        self.assertEqual(advance.state, "draft")
        self.assertTrue(advance.need_validation)

    def test_confirm_requests_two_tier_validation(self):
        advance = self._create_advance()
        advance.action_confirm()
        self.assertEqual(advance.state, "waiting_approval")
        self.assertEqual(len(advance.review_ids), 2)
        self.assertIn(advance.validation_status, ("pending", "waiting"))

    def test_confirm_before_validation_raises(self):
        advance = self._create_advance()
        advance.action_confirm()
        with self.assertRaises(UserError):
            advance.action_confirm()

    def test_first_tier_approval_still_pending(self):
        advance = self._create_advance()
        advance.action_confirm()
        advance.with_user(self.supervisor).validate_tier()
        advance.invalidate_recordset()
        statuses = advance.review_ids.sorted("sequence").mapped("status")
        self.assertEqual(statuses, ["approved", "pending"])
        self.assertEqual(advance.validation_status, "pending")

    def test_second_tier_approval_validates(self):
        advance = self._create_advance()
        advance.action_confirm()
        advance.with_user(self.supervisor).validate_tier()
        advance.invalidate_recordset()
        self.assertNotEqual(advance.validation_status, "validated")
        advance.with_user(self.accountant).validate_tier()
        advance.invalidate_recordset()
        self.assertEqual(advance.validation_status, "validated")

    def test_approve_after_full_validation(self):
        advance = self._create_advance()
        self._approve_advance(advance)
        self.assertEqual(advance.state, "approved")

    # ------------------------------------------------------------------
    # Payment
    # ------------------------------------------------------------------
    def test_pay_before_approval_raises(self):
        advance = self._create_advance()
        with self.assertRaises(UserError):
            advance.action_pay()

    def test_pay_creates_posted_payment(self):
        advance = self._create_advance(10000.0)
        self._approve_advance(advance)
        advance.action_pay()
        advance.invalidate_recordset()

        self.assertEqual(advance.state, "paid")
        self.assertTrue(advance.payment_id)
        self.assertIn(advance.payment_id.state, ("in_process", "paid"))

        receivable_lines = advance.payment_id.move_id.line_ids.filtered(
            lambda line: line.account_id == self.advance_account
        )
        self.assertAlmostEqual(sum(receivable_lines.mapped("debit")), 10000.0)
        self.assertAlmostEqual(sum(receivable_lines.mapped("credit")), 0.0)
        self.assertAlmostEqual(advance.remaining_amount, 10000.0)

    # ------------------------------------------------------------------
    # Clearing
    # ------------------------------------------------------------------
    def test_clear_advance_zeroes_employee_receivable(self):
        advance = self._create_paid_advance(10000.0)
        expense = self._create_expense(10000.0)

        wizard = self.env["od19.hr.advance.clear"].create({
            "advance_id": advance.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "expense_ids": [Command.set([expense.id])],
        })
        wizard.action_clear()
        advance.invalidate_recordset()

        self.assertEqual(advance.state, "cleared")
        self.assertAlmostEqual(advance.cleared_amount, 10000.0)
        self.assertAlmostEqual(advance.remaining_amount, 0.0)
        self.assertEqual(expense.od19_hr_advance_id, advance)
        self.assertTrue(advance.clear_move_id)

        receivable_lines = self.env["account.move.line"].search([
            ("account_id", "=", self.advance_account.id),
            ("partner_id", "=", self.employee_partner.id),
        ])
        self.assertTrue(all(receivable_lines.mapped("reconciled")))
        self.assertAlmostEqual(
            sum(receivable_lines.mapped("amount_residual")), 0.0
        )

    def test_clear_advance_with_returned_cash(self):
        advance = self._create_paid_advance(10000.0)
        expense = self._create_expense(8000.0)

        wizard = self.env["od19.hr.advance.clear"].create({
            "advance_id": advance.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "journal_id": self.bank_journal.id,
            "expense_ids": [Command.set([expense.id])],
            "returned_amount": 2000.0,
        })
        wizard.action_clear()
        advance.invalidate_recordset()

        self.assertEqual(advance.state, "cleared")
        self.assertAlmostEqual(advance.remaining_amount, 0.0)

        returned_lines = advance.clear_move_id.line_ids.filtered(
            lambda line: line.account_id == self.bank_journal.default_account_id
        )
        self.assertAlmostEqual(sum(returned_lines.mapped("debit")), 2000.0)

    def test_clear_exceeding_remaining_raises(self):
        advance = self._create_paid_advance(10000.0)
        expense = self._create_expense(15000.0)

        wizard = self.env["od19.hr.advance.clear"].create({
            "advance_id": advance.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "expense_ids": [Command.set([expense.id])],
        })
        with self.assertRaises(UserError):
            wizard.action_clear()

    def test_clear_requires_paid_state(self):
        advance = self._create_advance()
        self._approve_advance(advance)
        expense = self._create_expense(10000.0)
        wizard = self.env["od19.hr.advance.clear"].create({
            "advance_id": advance.id,
            "clear_date": fields.Date.context_today(self.env.user),
            "expense_ids": [Command.set([expense.id])],
        })
        with self.assertRaises(UserError):
            wizard.action_clear()

    # ------------------------------------------------------------------
    # Cancel / reset
    # ------------------------------------------------------------------
    def test_cancel_and_reset_to_draft(self):
        advance = self._create_advance()
        advance.action_cancel()
        self.assertEqual(advance.state, "cancel")
        advance.action_draft()
        self.assertEqual(advance.state, "draft")
