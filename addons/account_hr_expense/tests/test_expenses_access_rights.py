# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, UserError
from odoo.tests import Form, new_test_user, tagged

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

    def test_billing_user_opens_expense_entry(self):
        """ Test that a billing user doesn't raise errors when opening expense related entry """
        billing_user = new_test_user(self.env, login='expense_billing', groups='base.group_user,account.group_account_invoice')
        expense = self.create_expenses({'name': "Hotel"})
        expense.action_submit()
        expense.action_approve()
        self.post_expenses(expense)
        move = expense.account_move_id.with_user(billing_user)
        self.env.invalidate_all()  # The setup cached the expense, its reads by the billing user must check the access
        Form(move)
        with self.assertRaises(AccessError):
            move.action_open_expense()

        action = expense.account_move_id.with_user(self.expense_user_manager).action_open_expense()
        self.assertEqual(action['res_id'], expense.id)

    def test_employee_without_approver_submits_with_accounting(self):
        """ An employee without approver has their expense approved on submission, with its draft entry, as themselves """
        for login, groups in (
            ('expense_no_approver_light', 'base.group_user'),
            ('expense_no_approver_regular', 'base.group_user,base.group_user_regular'),
        ):
            with self.subTest(login=login):
                user = new_test_user(self.env, login=login, groups=groups)
                employee = self.env['hr.employee'].sudo().create({'name': login, 'user_id': user.id, 'work_contact_id': user.partner_id.id})
                expense = self.env['hr.expense'].with_user(user).create({
                    'name': "Without approver",
                    'employee_id': employee.id,
                    'product_id': self.product_c.id,
                    'total_amount_currency': 100.0,
                })
                expense.with_user(user).action_submit()
                # The approver is the user despite the sudo: the chatter author comes from the same `env.user`
                self.assertRecordValues(expense, [{'state': 'approved', 'manager_id': user.id}])
                self.assertEqual(expense.account_move_id.state, 'draft')

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

    def test_expense_locked_once_entry_posted(self):
        """ Posting the receipt locks the expense, although it stays approved until its payment """
        expense = self.create_expenses({'name': 'Expense to lock'})
        expense.action_submit()
        expense.action_approve()
        self.assertRecordValues(expense, [{'state': 'approved', 'is_editable': True, 'can_edit_account': True}])

        self.post_expenses(expense)
        self.assertRecordValues(expense, [{'state': 'approved', 'is_editable': False, 'can_edit_account': False}])
        with self.assertRaises(UserError):
            expense.action_split_wizard()

    def test_accounting_fields_of_non_editable_expense(self):
        """ An accountant sets the account and the analytics of an approved expense until its entry is posted, never its taxes """
        accountant = new_test_user(self.env, login='accountant_without_expense_rights', groups='base.group_user,account.group_account_user')
        expense = self.create_expenses({'name': 'Expense to account'})
        expense.action_submit()
        expense.action_approve()
        expense_as_accountant = expense.with_user(accountant)
        self.assertRecordValues(expense_as_accountant, [{'is_editable': False, 'can_edit_account': True}])

        expense_as_accountant.account_id = self.expense_account
        expense_as_accountant.analytic_distribution = {str(self.analytic_account_1.id): 100}
        with self.assertRaises(UserError):
            expense_as_accountant.tax_ids = self.tax_purchase_b

        self.post_expenses(expense)
        expense_as_accountant.invalidate_recordset()
        with self.assertRaises(UserError):
            expense_as_accountant.account_id = self.company_data['default_account_expense']
        with self.assertRaises(UserError):
            expense_as_accountant.analytic_distribution = {str(self.analytic_account_2.id): 100}

    def test_pay_requires_accounting_rights(self):
        """ Paying goes through the payment wizard of the receipt, which requires to be able to register payments """
        expense = self.create_expenses({'name': 'Expense to pay'})
        expense.action_submit()
        expense.action_approve()
        self.assertFalse(expense.can_pay, "The payment is registered on the journal entry, once posted")
        self.post_expenses(expense)
        self.assertTrue(expense.can_pay)

        expense_approver = new_test_user(
            self.env,
            login='expense_approver_no_account',
            groups='base.group_user,hr_expense.group_hr_expense_user',
        )
        self.assertFalse(expense.with_user(expense_approver).can_pay)
        with self.assertRaises(AccessError):
            expense.with_user(expense_approver).action_pay()

        action = expense.action_pay()
        self.assertEqual(action['res_model'], 'account.payment.register')
