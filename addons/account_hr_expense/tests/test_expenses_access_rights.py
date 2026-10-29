# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import new_test_user, tagged

from odoo.addons.account_hr_expense.tests.common import TestAccountExpenseCommon


@tagged('-at_install', 'post_install')
class TestAccountExpensesAccessRights(TestAccountExpenseCommon):

    _test_user_groups = None  # FIXME list needed groups

    def test_employee_rule_is_swapped(self):
        """ The employee rule of `hr_expense` can't know about the journal entries: it is replaced by the one of this module """
        employee_rule = self.env.ref('hr_expense.ir_rule_hr_expense_employee')
        employee_rule_account = self.env.ref('account_hr_expense.ir_rule_hr_expense_employee_account')
        self.assertFalse(employee_rule.active)
        self.assertTrue(employee_rule_account.active)

    def test_expense_manager_cannot_edit_expense_with_posted_entry(self):
        """ The manager of the employee can edit the approved expense, until the journal entry of the receipt is posted """
        # A simple user, without the rights on all the expenses, as the ones of the expense managers aren't restricted by the rule
        expense_manager = new_test_user(self.env, login='expense_manager_simple', groups='base.group_user')
        self.expense_employee.sudo().expense_manager_id = expense_manager
        expense = self.create_expenses({'name': 'Expense to post'})
        expense.action_submit()
        expense.action_approve()
        expense_as_manager = expense.with_user(expense_manager)
        self.assertEqual(expense.account_move_id.state, 'draft')
        self.assertTrue(expense_as_manager.has_access('write'))

        self.post_expenses(expense)
        self.assertEqual(expense.state, 'approved')
        expense_as_manager.invalidate_recordset()
        self.assertFalse(expense_as_manager.has_access('write'))
        self.assertTrue(expense_as_manager.has_access('read'))

    def test_pay_requires_accounting_rights(self):
        """ Paying goes through the payment wizard of the receipt, which requires to be able to register payments """
        expense = self.create_expenses({'name': 'Expense to pay'})
        expense.action_submit()
        expense.action_approve()
        self.post_expenses(expense)

        expense_approver = new_test_user(
            self.env,
            login='expense_approver_no_account',
            groups='base.group_user,hr_expense.group_hr_expense_user',
        )
        with self.assertRaises(AccessError):
            expense.with_user(expense_approver).action_pay()

        action = expense.action_pay()
        self.assertEqual(action['res_model'], 'account.payment.register')
