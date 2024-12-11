# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestExpensesStates(TestExpenseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.expense_states_employee = cls.create_expenses({
            'name': 'Expense Employee 1',
        })

        cls.expense_states_company = cls.create_expenses({
            'name': 'Expense Company 1',
            'payment_mode': 'company_account',
        })
        cls.expense_states = cls.expense_states_employee + cls.expense_states_company

        cls.paid_or_in_payment_state = cls.env['account.move']._get_invoice_in_payment_state()

    def test_expense_state_synchro_1_regular_flow(self):
        # STEP 1: Draft
        self.assertRecordValues(self.expense_states, [
            {'payment_mode': 'own_account', 'state': 'draft', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'draft', 'payment_state': 'not_paid'},
        ])
        self.assertFalse(self.expense_states.account_move_id)

        # STEP 2: Submit
        self.expense_states.action_submit()
        self.assertRecordValues(self.expense_states, [
            {'payment_mode': 'own_account', 'state': 'submitted', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'submitted', 'payment_state': 'not_paid'},
        ])
        self.assertFalse(self.expense_states.account_move_id)

        # STEP 3: Approve (creates moves in draft)
        self.expense_states.action_approve()
        self.assertRecordValues(self.expense_states, [
            {'payment_mode': 'own_account', 'state': 'approved', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'approved', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])
        self.assertEqual('draft', self.expense_states_company.account_move_id.origin_payment_id.state)
        self.assertFalse(self.expense_states_employee.account_move_id.origin_payment_id)

        # STEP 4: Post
        self.expense_states.action_post()
        self.assertRecordValues(self.expense_states, [
            {'payment_mode': 'own_account', 'state': 'posted', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'posted', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states.account_move_id, [
            {'state': 'posted', 'payment_state': 'not_paid'},
            {'state': 'posted', 'payment_state': 'not_paid'},
        ])

        self.assertEqual('in_process', self.expense_states_company.account_move_id.origin_payment_id.state)
        self.assertFalse(self.expense_states_employee.account_move_id.origin_payment_id)

    def test_expense_state_synchro_2_employee_specific_flow_1(self):
        """ Posted -> Reset move to draft (back to approved step)"""
        self.expense_states.action_submit()
        self.expense_states.action_approve()
        self.expense_states.action_sheet_move_post()

        self.expense_states_employee.account_move_id.button_draft()
        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'approved', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_2(self):
        """ Approved with draft move -> Cancel move (Approved without move) """
        self.expense_states.action_submit()
        self.expense_states.action_approve()

        self.expense_states_employee.account_move_id.button_cancel()
        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'approved', 'payment_state': 'not_paid', 'account_move_id': False},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_3(self):
        """ Approved with draft move -> unlink move (Approved without move) """
        self.expense_states.action_submit()
        self.expense_states.action_approve()

        self.expense_states_employee.account_move_id.unlink()
        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'approved', 'payment_state': 'not_paid', 'account_move_id': False},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_4(self):
        """ Posted -> Reverse move (Reverts to approve state without move) """
        self.expense_states.action_submit()
        self.expense_states.action_approve()
        self.expense_states.action_post()

        self.expense_states_employee.account_move_id._reverse_moves(
            default_values_list=[{'invoice_date': fields.Date.context_today(self.expense_states_employee)}],
            cancel=True,
        )
        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'approved', 'payment_state': 'not_paid', 'account_move_id': False},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_5(self):
        """ Approved without draft -> Post (Creates move and post expense & move) """
        self.expense_states.action_submit()
        self.expense_states.action_approve()
        self.expense_states.account_move_id.unlink()
        self.expense_states.action_post()

        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'posted', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee.account_move_id, [
            {'state': 'posted', 'payment_state': 'not_paid'},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_6(self):
        """ Posted -> Paid in one payment (Set to paid) """
        self.expense_states.action_submit()
        self.expense_states.action_approve()
        self.expense_states.account_move_id.unlink()
        self.expense_states.action_post()

        action_context = self.expense_states_employee.action_register_payment()['context']
        self.env['account.payment.register'] \
            .with_context(action_context) \
            .create({'amount': self.expense_states_employee.total_amount}) \
            ._create_payments()

        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])
        self.assertRecordValues(self.expense_states_employee.account_move_id, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_7(self):
        """ Posted -> Paid in several payment (Set to paid, even when partially)"""
        self.expense_states.action_submit()
        self.expense_states.action_approve()
        self.expense_states.account_move_id.unlink()
        self.expense_states.action_post()

        action_context = self.expense_states_employee.action_register_payment()['context']
        self.env['account.payment.register'] \
            .with_context(action_context) \
            .create({'amount': 1}) \
            ._create_payments()

        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])
        self.assertRecordValues(self.expense_states_employee.account_move_id, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])

        action_context = self.expense_states_employee.action_register_payment()['context']
        self.env['account.payment.register'] \
            .with_context(action_context) \
            .create({'amount': self.expense_states_employee.total_amount - 1}) \
            ._create_payments()

        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])
        self.assertRecordValues(self.expense_states_employee.account_move_id, [
            {'state': 'posted', 'payment_state': 'partial'},
        ])

    def test_expense_state_synchro_2_employee_specific_flow_8(self):
        """ (Partially/) Paid -> Reset move to draft (Back to approved with draft move state and "not paid" payment state) """
        self.expense_states.action_submit()
        self.expense_states.action_approve()
        self.expense_states.action_post()

        action_context = self.expense_states_employee.action_register_payment()['context']
        self.env['account.payment.register'].with_context(action_context).create({})._create_payments()

        self.expense_states_employee.account_move_id.button_draft()
        self.assertRecordValues(self.expense_states_employee, [
            {'state': 'approved', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])

    def test_expense_state_synchro_3_company_specific_flow_1(self):
        """ Posted & paid -> Reset move or payment to draft (back to approved stage) """
        self.expense_states_company.action_submit()
        self.expense_states_company.action_approve()
        self.expense_states_company.action_post()

        self.expense_states_company.account_move_id.button_draft()
        self.assertRecordValues(self.expense_states_company, [
            {'state': 'approved', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_company.account_move_id, [
            {'state': 'draft', 'payment_state': 'not_paid'},
        ])

        self.expense_states_company.account_move_id.action_post()
        self.assertRecordValues(self.expense_states_company, [
            {'state': 'posted', 'payment_state': 'paid'},
        ])
        self.expense_states_company.account_move_id.origin_payment_id.action_draft()
        self.assertRecordValues(self.expense_states_company, [
            {'state': 'approved', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_company.account_move_id, [
            {'state': 'draft'},
        ])

    def test_expense_state_synchro_3_company_specific_flow_2(self):
        """ Approved with draft move -> Cancel move (stays approved, without linked move) """
        self.expense_states_company.action_submit()
        self.expense_states_company.action_approve()
        self.expense_states_company.action_post()

        self.expense_states_company.account_move_id.button_cancel()
        self.assertRecordValues(self.expense_states_company, [
            {'state': 'approved', 'payment_state': 'not_paid', 'account_move_id': False},
        ])

    def test_expense_state_synchro_3_company_specific_flow_3(self):
        """ Approved with draft move -> Cancel payment (approved stage, without linked move) """
        self.expense_states_company.action_submit()
        self.expense_states_company.action_approve()
        self.expense_states_company.action_post()

        self.expense_states_company.account_move_id.origin_payment_id.button_cancel()
        self.assertRecordValues(self.expense_states_company, [
            {'state': 'approved', 'payment_state': 'not_paid', 'account_move_id': False},
        ])

    def test_expense_state_synchro_3_company_specific_flow_4(self):
        """ Approved with draft move -> Delete move (approved stage, without linked move) """
        self.expense_states_company.action_submit()
        self.expense_states_company.action_approve()
        self.expense_states_company.action_post()

        self.expense_states_company.account_move_id.unlink()
        self.assertRecordValues(self.expense_states_company, [
            {'state': 'approved', 'payment_state': 'not_paid', 'account_move_id': False},
        ])

    def test_expense_state_synchro_3_company_specific_flow_5(self):
        """ Posted & Paid -> Reverse move (Change payment state to 'reversed') """
        self.expense_states_company.action_submit()
        self.expense_states_company.action_approve()
        self.expense_states_company.action_post()

        self.expense_states_company.account_move_id._reverse_moves(
            default_values_list=[{'invoice_date': fields.Date.context_today(self.expense_states_company_sheet)}],
            cancel=True,
        )
        self.assertRecordValues(self.expense_states_company, [
            {'state': 'done', 'payment_state': 'reversed'},
        ])
        self.assertRecordValues(self.expense_states_company.account_move_id, [
            {'state': 'posted'},
        ])
