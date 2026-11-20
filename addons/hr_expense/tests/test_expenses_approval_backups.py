# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import new_test_user, tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('post_install', '-at_install')
class TestExpensesApprovalBackups(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company_ids = [Command.set(cls.env.companies.ids)]
        cls.approver_user = new_test_user(cls.env, login='approver', company_ids=company_ids)
        cls.backup_user = new_test_user(cls.env, login='backup', company_ids=company_ids)
        cls.stranger_user = new_test_user(
            cls.env, login='stranger', groups='base.group_user,hr_expense.group_hr_expense_team_approver',
            company_ids=company_ids,
        )
        # sudo: the user of TestExpenseCommon is an accountant, not an HR officer
        cls.approver_employee, cls.backup_employee = cls.env['hr.employee'].sudo().create([
            {'name': 'Approver', 'user_id': cls.approver_user.id},
            {'name': 'Backup', 'user_id': cls.backup_user.id, 'expense_manager_id': cls.approver_user.id},
        ])
        cls.expense_employee.sudo().expense_manager_id = cls.approver_user
        cls.approver_employee.approval_backups = cls.backup_user

    def _submitted_expense(self, employee=None):
        employee = employee or self.expense_employee
        expense = self.create_expenses({'name': 'Lunch', 'employee_id': employee.id})
        expense.with_user(employee.user_id).action_submit()
        self.assertEqual(expense.state, 'submitted')
        return expense

    def test_approver_and_backup_get_team_approver_group(self):
        for user in (self.approver_user, self.backup_user):
            self.assertTrue(user.has_group('hr_expense.group_hr_expense_team_approver'))
            self.assertEqual(user.role, 'regular_user')

    def test_any_internal_user_can_be_approver(self):
        light_user = new_test_user(self.env, login='light', company_ids=[Command.set(self.env.companies.ids)])
        self.assertEqual(light_user.role, 'light_user')
        self.backup_employee.expense_manager_id = light_user
        self.assertTrue(light_user.has_group('hr_expense.group_hr_expense_team_approver'))
        self.assertEqual(light_user.role, 'regular_user')

    def test_backup_can_approve(self):
        expense = self._submitted_expense()
        self.env.invalidate_all()
        self.assertEqual(self.env['hr.expense'].with_user(self.backup_user).search([('id', '=', expense.id)]), expense)
        self.assertFalse(self.env['hr.expense'].with_user(self.stranger_user).search([('id', '=', expense.id)]))
        expense_as_backup = expense.with_user(self.backup_user)
        self.assertTrue(expense_as_backup.can_approve)
        expense_as_backup.action_approve()
        self.assertEqual(expense.state, 'approved')
        # the backup is the one who approved
        self.assertEqual(expense.manager_id, self.backup_user)

    def test_backup_cannot_approve_own_expense(self):
        expense = self._submitted_expense(self.backup_employee)
        self.env.invalidate_all()
        self.assertFalse(expense.with_user(self.backup_user).can_approve)

    def test_removed_backup_loses_access(self):
        expense = self._submitted_expense()
        self.approver_employee.approval_backups = False
        self.env.invalidate_all()
        self.assertFalse(self.env['hr.expense'].with_user(self.backup_user).search([('id', '=', expense.id)]))
