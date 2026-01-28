# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.mail.tests.common import MailCase
from odoo import fields
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestExpensesStates(TestExpenseCommon, MailCase):
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

        cls.paid_or_in_payment_state = cls.env['account.move']._get_invoice_in_payment_state()

    def test_expense_state_synchro_1_regular_flow(self):
        # STEP 1: Draft
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'draft'},
            {'payment_mode': 'company_account', 'state': 'draft'},
        ])
        self.assertFalse(self.expenses_all.account_move_id)

        # STEP 2: Submit
        self.expenses_all.action_submit()
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'submitted'},
            {'payment_mode': 'company_account', 'state': 'submitted'},
        ])
        self.assertFalse(self.expenses_all.account_move_id)

        # STEP 3: Approve
        self.expenses_all.action_approve()
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'approved'},
            {'payment_mode': 'company_account', 'state': 'approved'},
        ])
        self.assertFalse(self.expenses_all.account_move_id)

        # STEP 4: Post (create moves)
        self.post_expenses_with_wizard(self.expenses_all)
        self.assertRecordValues(self.expenses_all, [
            {'payment_mode': 'own_account',     'state': 'posted'},
            {'payment_mode': 'company_account', 'state': 'paid'},
        ])
        self.assertRecordValues(self.expenses_all.account_move_id, [
            {'state': 'posted', 'payment_state': 'not_paid'},
            {'state': 'posted', 'payment_state': 'not_paid'},
        ])

        self.assertEqual('in_process', self.expenses_company.account_move_id.origin_payment_id.state)
        self.assertFalse(self.expenses_employee.account_move_id.origin_payment_id)

    def test_expense_state_synchro_1_cancel_move(self):
        """ Posted -> Cancel move (Back to approved) """
        self.expenses_all.action_submit()
        self.expenses_all.action_approve()
        self.post_expenses_with_wizard(self.expenses_all)

        self.expenses_all.account_move_id.button_draft()
        self.expenses_all.account_move_id.button_cancel()
        self.assertRecordValues(self.expenses_all, [
            {'state': 'approved', 'account_move_id': False},
            {'state': 'approved', 'account_move_id': False},
        ])
        self.assertFalse(self.expenses_all.account_move_id)

    def test_expense_state_synchro_1_unlink_move(self):
        """ Posted -> Unlink move/payment (Back to approved) """
        self.expenses_all.action_submit()
        self.expenses_all.action_approve()
        self.post_expenses_with_wizard(self.expenses_all)

        self.expenses_all.account_move_id.button_draft()
        self.expenses_all.account_move_id.origin_payment_id.unlink()
        self.expenses_all.account_move_id.unlink()
        self.assertRecordValues(self.expenses_all, [
            {'state': 'approved', 'account_move_id': False},
            {'state': 'approved', 'account_move_id': False},
        ])

    def test_expense_state_synchro_1_reverse_move(self):
        """ Posted -> Reverse move (Back to approved) """
        self.expenses_all.action_submit()
        self.expenses_all.action_approve()
        self.post_expenses_with_wizard(self.expenses_all)

        self.expenses_all.account_move_id._reverse_moves(
            default_values_list=[{'invoice_date': fields.Date.context_today(self.expenses_all)}],
            cancel=True,
        )
        self.assertRecordValues(self.expenses_all, [
            {'state': 'approved', 'account_move_id': False},
            {'state': 'approved', 'account_move_id': False},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_1(self):
        """ Posted -> Reset move to draft (No change)"""
        self.expenses_employee.action_submit()
        self.expenses_employee.action_approve()
        self.post_expenses_with_wizard(self.expenses_employee)

        self.expenses_employee.account_move_id.button_draft()
        self.assertEqual(self.expenses_employee.state, 'posted')
        self.assertRecordValues(self.expenses_employee.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_2(self):
        """ Posted -> Paid in one payment (Set to paid) """
        self.expenses_employee.action_submit()
        self.expenses_employee.action_approve()
        self.post_expenses_with_wizard(self.expenses_employee)

        self.get_new_payment(self.expenses_employee, self.expenses_employee.total_amount)

        self.assertEqual(self.expenses_employee.state, self.paid_or_in_payment_state)
        self.assertRecordValues(self.expenses_employee.account_move_id, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_3(self):
        """ Posted -> Paid in several payment (Set to paid, even when partially)"""
        self.expenses_employee.action_submit()
        self.expenses_employee.action_approve()
        self.post_expenses_with_wizard(self.expenses_employee)

        self.get_new_payment(self.expenses_employee, 1)

        self.assertEqual(self.expenses_employee.state, self.paid_or_in_payment_state)
        self.assertRecordValues(self.expenses_employee.account_move_id, [
            {'state': 'posted', 'payment_state': 'partial'},
        ])

        self.get_new_payment(self.expenses_employee, self.expenses_employee.total_amount - 1)

        self.assertEqual(self.expenses_employee.state, self.paid_or_in_payment_state)
        self.assertRecordValues(self.expenses_employee.account_move_id, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_4(self):
        """ (Partially/) Paid -> Reset move to draft (Back to posted) """
        self.expenses_employee.action_submit()
        self.expenses_employee.action_approve()
        self.post_expenses_with_wizard(self.expenses_employee)

        self.get_new_payment(self.expenses_employee, self.expenses_employee.total_amount)

        self.expenses_employee.account_move_id.button_draft()
        self.expenses_employee.account_move_id.line_ids.remove_move_reconcile()
        self.assertEqual(self.expenses_employee.state, 'posted')
        self.assertRecordValues(self.expenses_employee.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])

    def test_expense_state_synchro_3_company_specific_flow(self):
        """ Paid -> Reset move or payment to draft (Stay paid) """
        self.expenses_company.action_submit()
        self.expenses_company.action_approve()
        self.expenses_company.action_post()

        self.expenses_company.account_move_id.button_draft()
        self.assertEqual(self.expenses_company.state, 'paid')
        self.assertRecordValues(self.expenses_company.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])

        self.expenses_company.account_move_id.action_post()
        self.assertEqual(self.expenses_company.state, 'paid')

        self.expenses_company.account_move_id.origin_payment_id.action_draft()
        self.assertEqual(self.expenses_company.state, 'paid')
        self.assertRecordValues(self.expenses_company.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])

    def test_expense_state_autovalidation(self):
        """ Test the auto-validation flow skips 'submitted' state when there is no manager"""
        self.expense_employee.sudo().expense_manager_id = False
        self.expenses_all.sudo().manager_id = False
        self.expenses_all.action_submit()
        self.assertSequenceEqual(['approved', 'approved'], self.expenses_all.mapped('state'))

    def test_expense_next_activity(self):
        """ Test next activity is assigned to the right manager, no notification is sent, but validation email is sent"""
        self.expenses_employee.manager_id = self.expense_user_manager_2
        with self.mock_mail_gateway():
            self.expenses_employee.action_submit()
            self.env['hr.expense']._cron_send_submitted_expenses_mail()
        mail_activity = self.env['mail.activity'].search([('res_model', '=', 'hr.expense'), ('res_id', '=', self.expenses_employee.id)])
        self.assertEqual(mail_activity.user_id.id, self.expense_user_manager_2.id)
        # No notification should be sent
        notification_message = self.env['mail.message'].search([('partner_ids', 'in', self.expense_user_manager_2.partner_id.ids), ('display_name', '=', mail_activity.res_name)])
        self.assertFalse(notification_message)
        # Expenses submitted email is sent via cron
        expenses_submitted = self.env['mail.mail'].search(
            [('email_to', '=', self.expense_user_manager_2.email),
            ('subject', '=', "New expenses waiting for your approval")]
            )
        self.assertEqual(len(expenses_submitted), 1)
