# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.exceptions import AccessError, UserError
from odoo.tests import HttpCase, tagged, new_test_user

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


@tagged('-at_install', 'post_install')
class TestExpensesAccessRights(TestExpenseCommon, HttpCase):

    def test_expense_access_rights(self):
        """ The expense employee can't be able to create an expense for someone else. """

        expense_employee_2 = self.env['hr.employee'].sudo().create({
            'name': 'expense_employee_2',
            'user_id': self.env.user.id,
            'work_contact_id': self.env.user.partner_id.id,
        }).sudo(False)

        with self.assertRaises(AccessError):
            self.env['hr.expense'].with_user(self.expense_user_employee).create({
                'name': "Superboy costume washing",
                'employee_id': expense_employee_2.id,
                'product_id': self.product_a.id,
                'quantity': 1,
            })

        expense = self.env['hr.expense'].with_user(self.expense_user_employee).create({
            'name': 'expense_1',
            'date': '2016-01-01',
            'product_id': self.product_a.id,
            'quantity': 10.0,
            'employee_id': self.expense_employee.id,
        })

        # The expense employee shouldn't be able to bypass the submit state.
        with self.assertRaises(UserError):
            expense.with_user(self.expense_user_employee).state = 'approved'
        expense.with_user(self.expense_user_employee).state = 'draft'  # Should not raise

        expense.with_user(self.expense_user_employee).action_submit()
        self.assertEqual(expense.state, 'submitted')

        # Employee can also revert from the submitted state to a draft state
        expense.with_user(self.expense_user_employee).action_reset()
        self.assertEqual(expense.state, 'draft')

    def test_expense_access_rights_user(self):
        # The expense base user (without other rights) is able to create and read sheet

        user = new_test_user(self.env, login='test-expense', groups='base.group_user')
        expense_employee = self.env['hr.employee'].sudo().create({
            'name': 'expense_employee_base_user',
            'user_id': user.id,
            'work_contact_id': user.partner_id.id,
            'expense_manager_id': self.expense_user_manager.id,
            'address_id': user.partner_id.id,
        }).sudo(False)

        expense = self.env['hr.expense'].with_user(user).create({
            'name': 'First Expense for employee',
            'employee_id': expense_employee.id,
            # Expense without foreign currency but analytic account.
            'product_id': self.product_a.id,
            'price_unit': 1000.0,
        })
        self.start_tour("/odoo", 'hr_expense_access_rights_test_tour', login="test-expense")
        self.assertRecordValues(expense, [{'state': 'submitted'}])

    def test_expense_user_cant_approve_own_expense(self):
        expense = self.env['hr.expense'].with_user(self.expense_user_employee).create({
            'name': "Superboy costume washing",
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'quantity': 1,
            'price_unit': 1,
        })
        expense.with_user(self.expense_user_employee).action_submit()
        with self.assertRaises(UserError):
            expense.with_user(self.expense_user_employee).action_approve()

    def test_expense_team_approver_cant_approve_expense_of_employee_he_does_not_manage(self):
        another_standard_user = new_test_user(self.env, login='another_standard_user', groups='base.group_user')
        another_standard_user_team_approver = new_test_user(self.env, login='another_standard_user_manager', groups='base.group_user,hr_expense.group_hr_expense_team_approver')

        another_employee = self.env['hr.employee'].sudo().create({
            'name': 'another_employee',
            'user_id': another_standard_user.id,
            'work_contact_id': another_standard_user.partner_id.id,
            'expense_manager_id': self.expense_user_manager.id,
        }).sudo(False)

        expense = self.env['hr.expense'].with_user(another_standard_user).create({
            'name': "Superboy costume washing",
            'employee_id': another_employee.id,
            'product_id': self.product_a.id,
            'quantity': 1,
            'price_unit': 1,
        })
        expense.with_user(another_standard_user).action_submit()
        with self.assertRaises(AccessError):
            expense.with_user(another_standard_user_team_approver).action_approve()
