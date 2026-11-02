# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo import fields
from odoo.exceptions import UserError


class TestHrExpenseThai(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.product = cls.env['product.product'].create({
            'name': 'Expense Product',
            'type': 'service',
        })
        # Reuse existing employee to avoid res.partner NOT NULL column issues
        cls.employee = cls.env['hr.employee'].search([], limit=1)
        if not cls.employee:
            cls.employee = cls.env['hr.employee'].create({'name': 'Test Employee'})

    def _create_expense(self, amount, payment_mode='own_account'):
        expense = self.env['hr.expense'].create({
            'name': 'Test Expense',
            'product_id': self.product.id,
            'total_amount': amount,
            'employee_id': self.employee.id,
            'payment_mode': payment_mode,
        })
        # Directly set approval state to avoid auto-validation in test env
        expense.approval_state = 'submitted'
        return expense

    def test_payment_method_default(self):
        """Default payment method should be cash."""
        expense = self._create_expense(100.0)
        self.assertEqual(expense.payment_method, 'cash')

    def test_thai_expense_type_default(self):
        """Default Thai expense type should be other."""
        expense = self._create_expense(100.0)
        self.assertEqual(expense.thai_expense_type, 'other')

    def test_require_second_approval_below_threshold(self):
        """Expenses below 5000 should not require second approval."""
        expense = self._create_expense(3000.0)
        self.assertFalse(expense.require_second_approval)

    def test_require_second_approval_above_threshold(self):
        """Expenses above 5000 should require second approval."""
        expense = self._create_expense(6000.0)
        self.assertTrue(expense.require_second_approval)

    def test_first_approval_no_second_required(self):
        """First approval auto-completes when second not required."""
        expense = self._create_expense(1000.0)
        expense.action_approve_first()
        self.assertEqual(expense.second_approval_state, 'approved')
        self.assertEqual(expense.state, 'approved')

    def test_first_approval_second_required(self):
        """First approval sets pending for second when required."""
        expense = self._create_expense(6000.0)
        expense.action_approve_first()
        self.assertEqual(expense.second_approval_state, 'pending')
        self.assertEqual(expense.first_approval_date, fields.Date.context_today(self.env.user))

    def test_second_approval(self):
        """Second approval completes the approval flow."""
        expense = self._create_expense(6000.0)
        expense.action_approve_first()
        expense.action_approve_second()
        self.assertEqual(expense.second_approval_state, 'approved')
        self.assertEqual(expense.state, 'approved')

    def test_mark_reimbursed_requires_posted_expense(self):
        """Reimbursement needs a posted journal entry: nothing to settle yet."""
        expense = self._create_expense(1000.0)
        with self.assertRaises(UserError):
            expense.action_mark_reimbursed()

    def test_mark_reimbursed_company_account_raises(self):
        """Mark reimbursed should fail for company account expenses."""
        expense = self._create_expense(1000.0, payment_mode='company_account')
        with self.assertRaises(Exception):
            expense.action_mark_reimbursed()
