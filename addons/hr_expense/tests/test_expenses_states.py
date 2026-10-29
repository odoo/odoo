# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged

from odoo.addons.hr_expense.tests.common import TestExpenseCommon, account_less_only
from odoo.addons.mail.tests.common import MailCase, mail_new_test_user


@tagged('-at_install', 'post_install')
class TestExpensesStates(TestExpenseCommon, MailCase):
    _test_user_groups = None  # FIXME list needed groups

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expenses_employee = cls.create_expenses({
            'name': 'Expense Employee 1',
        })

        cls.expenses_company = cls.create_expenses({
            'name': 'Expense Company 1',
            'payment_mode': 'company_account',
            # To avoid duplicated expense wizard
            'total_amount_currency': 1000,
            'date': '2017-01-01',
        })
        cls.expenses_all = cls.expenses_employee + cls.expenses_company

    @account_less_only
    def test_expense_state_synchro_1_regular_flow(self):
        # STEP 1: Draft
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'draft'},
            {'payment_mode': 'company_account', 'state': 'draft'},
        ])

        # STEP 2: Submit
        self.expenses_all.action_submit()
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'submitted'},
            {'payment_mode': 'company_account', 'state': 'submitted'},
        ])

        # STEP 3: Approve
        self.expenses_all.action_approve()
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'approved'},
            {'payment_mode': 'company_account', 'state': 'paid'},
        ])

        # STEP 4: The employee-paid expense is reimbursed, the company-paid one was already paid
        self.expenses_employee.action_pay()
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'paid'},
            {'payment_mode': 'company_account', 'state': 'paid'},
        ])

    def test_expense_company_paid_is_paid_on_approval(self):
        """ Without accounting, there is nothing left to do for an expense paid by the company once approved """
        self.expenses_company.action_submit()
        self.assertEqual(self.expenses_company.state, 'submitted')
        self.expenses_company.action_approve()
        self.assertEqual(self.expenses_company.state, 'paid')
        with self.assertRaises(UserError):  # Nothing to reimburse
            self.expenses_company.action_pay()

    @account_less_only
    def test_expense_employee_paid_needs_to_be_paid(self):
        """ An expense paid by the employee stays approved until someone marks it as paid """
        self.expenses_employee.action_submit()
        with self.assertRaises(UserError):  # Not approved yet
            self.expenses_employee.action_pay()
        self.expenses_employee.action_approve()
        self.assertEqual(self.expenses_employee.state, 'approved')
        self.assertFalse(self.expenses_employee.marked_as_paid)

        self.expenses_employee.action_pay()
        self.assertRecordValues(self.expenses_employee, [{'state': 'paid', 'marked_as_paid': True}])

        self.expenses_employee.action_reset()
        self.assertRecordValues(self.expenses_employee, [{'state': 'draft', 'marked_as_paid': False}])

    @account_less_only
    def test_expense_pay_access_rights(self):
        """ Only the approvers of all the expenses can pay, not the ones of a team """
        team_approver = mail_new_test_user(
            self.env,
            login='expense_team_approver_pay',
            groups='base.group_user,hr_expense.group_hr_expense_team_approver',
        )
        approver = mail_new_test_user(
            self.env,
            login='expense_approver_pay',
            groups='base.group_user,hr_expense.group_hr_expense_user',
        )
        self.expense_employee.sudo().parent_id = self.env['hr.employee'].sudo().create({
            'name': 'team_leader',
            'user_id': team_approver.id,
        })
        self.expenses_employee.action_submit()
        self.expenses_employee.action_approve()

        with self.assertRaises(AccessError):
            self.expenses_employee.with_user(team_approver).action_pay()
        self.assertEqual(self.expenses_employee.state, 'approved')

        self.expenses_employee.with_user(approver).action_pay()
        self.assertEqual(self.expenses_employee.state, 'paid')

    def test_expense_mandatory_analytic_plan_on_approval(self):
        """ A mandatory analytic plan of the expenses is checked when approving, as the approve buttons ask for """
        self.env['account.analytic.applicability'].create({
            'business_domain': 'expense',
            'analytic_plan_id': self.analytic_plan.id,
            'applicability': 'mandatory',
        })
        self.expenses_employee.action_submit()

        with self.assertRaises(ValidationError):
            self.expenses_employee.with_context(validate_analytic=True).action_approve()
        self.assertEqual(self.expenses_employee.state, 'submitted')

        self.expenses_employee.analytic_distribution = {self.analytic_account_1.id: 100}
        self.expenses_employee.with_context(validate_analytic=True).action_approve()
        self.assertEqual(self.expenses_employee.state, 'approved')

    def test_expense_state_autovalidation(self):
        """ Test the auto-validation flow skips 'submitted' state when there is no manager"""
        self.expense_employee.sudo().expense_manager_id = False
        self.expenses_all.sudo().manager_id = False
        self.expenses_all.action_submit()
        self.assertSequenceEqual(['approved', 'paid'], self.expenses_all.mapped('state'))

    def test_expense_next_activity(self):
        """ Test next activity is assigned to the right manager, no notification is sent, but validation email is sent"""
        self.expenses_employee.manager_id = self.expense_user_manager_2
        with self.mock_mail_gateway():
            self.expenses_employee.action_submit()
        mail_activity = self.env['mail.activity'].search([('res_model', '=', 'hr.expense'), ('res_id', '=', self.expenses_employee.id)])
        self.assertEqual(mail_activity.user_id.id, self.expense_user_manager_2.id)
        # No notification should be sent
        notification_message = self.env['mail.message'].search([('partner_ids', 'in', self.expense_user_manager_2.partner_id.ids), ('display_name', '=', mail_activity.res_name)])
        self.assertFalse(notification_message)
        # Expenses submitted email was sent on submission
        expenses_submitted = self.env['mail.mail'].search(
            [('email_to', '=', self.expense_user_manager_2.email),
            ('subject', '=', "New expenses waiting for your approval")]
            )
        self.assertEqual(len(expenses_submitted), 1)
