# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestExpensesStates(TestExpenseCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.expense_states_employee_sheet = cls.env['hr.expense.sheet'].create({
            'name': 'Expense Employee 1',
            'employee_id': cls.expense_employee.id,
            'expense_line_ids': [Command.create({
                'name': 'Expense Employee 1',
                'employee_id': cls.expense_employee.id,
                'product_id': cls.product_c.id,
                'total_amount': 100.00,
            })],
        })

        cls.expense_states_company_sheet = cls.env['hr.expense.sheet'].create({
            'name': 'Expense Company 1',
            'employee_id': cls.expense_employee.id,
            'expense_line_ids': [Command.create({
                'name': 'Expense Company 1',
                'payment_mode': 'company_account',
                'employee_id': cls.expense_employee.id,
                'product_id': cls.product_c.id,
                'total_amount': 100.00,
            })],
        })
        cls.expense_states_sheets = cls.expense_states_employee_sheet + cls.expense_states_company_sheet

        cls.paid_or_in_payment_state = cls.env['account.move']._get_invoice_in_payment_state()

    def test_expense_state_synchro_1_regular_flow(self):
        # STEP 1: Draft
        self.assertRecordValues(self.expense_states_sheets.expense_line_ids, [
            {'payment_mode': 'own_account', 'state': 'draft'},
            {'payment_mode': 'company_account', 'state': 'draft'},
        ])
        self.assertRecordValues(self.expense_states_sheets, [
            {'payment_mode': 'own_account', 'state': 'draft', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'draft', 'payment_state': 'not_paid'},
        ])
        self.assertFalse(self.expense_states_sheets.account_move_id)

        # STEP 2: Submit
        self.expense_states_sheets.action_submit_sheet()
        self.assertRecordValues(self.expense_states_sheets.expense_line_ids, [
            {'payment_mode': 'own_account', 'state': 'reported'},
            {'payment_mode': 'company_account', 'state': 'reported'},
        ])
        self.assertRecordValues(self.expense_states_sheets, [
            {'payment_mode': 'own_account', 'state': 'submit', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'submit', 'payment_state': 'not_paid'},
        ])

        # STEP 3: Approve
        self.expense_states_sheets.approve_expense_sheets()
        self.assertRecordValues(self.expense_states_sheets.expense_line_ids, [
            {'payment_mode': 'own_account', 'state': 'approved'},
            {'payment_mode': 'company_account', 'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_sheets, [
            {'payment_mode': 'own_account', 'state': 'approve', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'approve', 'payment_state': 'not_paid'},
        ])
        self.assertFalse(self.expense_states_sheets.account_move_id)

        # STEP 4: Post
        self.expense_states_sheets.action_sheet_move_create()
        self.assertRecordValues(self.expense_states_sheets.expense_line_ids, [
            {'payment_mode': 'own_account', 'state': 'approved'},
            {'payment_mode': 'company_account', 'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_sheets, [
            {'payment_mode': 'own_account', 'state': 'post', 'payment_state': 'not_paid'},
            {'payment_mode': 'company_account', 'state': 'done', 'payment_state': 'paid'},
        ])
        self.assertRecordValues(self.expense_states_sheets.account_move_id, [
            {'state': 'posted'},
            {'state': 'posted'},
        ])

    def test_expense_state_synchro_2_employee_specific_flow(self):
        self.expense_states_sheets.action_submit_sheet()
        self.expense_states_sheets.approve_expense_sheets()
        self.expense_states_sheets.action_sheet_move_create()

        # STEP 1: ER posted -> Reset move to draft
        self.expense_states_employee_sheet.account_move_id.button_draft()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'post', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'draft'},
        ])

        # STEP 2: ER posted with draft move -> Cancel move (nothing changes)
        self.expense_states_employee_sheet.account_move_id.button_cancel()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'post', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'cancel'},
        ])

        # Change move state to draft
        self.expense_states_employee_sheet.account_move_id.button_draft()

        # STEP 3: ER posted with draft move -> unlink move (Reverts to approve state)
        self.expense_states_employee_sheet.account_move_id.unlink()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'approve', 'payment_state': 'not_paid'},
        ])
        self.assertFalse(self.expense_states_employee_sheet.account_move_id)

        # Re-create posted move
        self.expense_states_employee_sheet.action_sheet_move_create()

        # STEP 4: ER with draft move -> Reverse move (Reverts to approve state)
        self.expense_states_employee_sheet.account_move_id._reverse_moves(
            default_values_list=[{'invoice_date': fields.Date.context_today(self.expense_states_employee_sheet)}],
            cancel=True,
        )
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'approve', 'payment_state': 'not_paid'},
        ])
        self.assertFalse(self.expense_states_employee_sheet.account_move_id)

        # Change the report state to a partially paid one
        self.expense_states_employee_sheet.action_sheet_move_create()
        action_context = self.expense_states_employee_sheet.action_register_payment()['context']
        self.env['account.payment.register'].with_context(action_context).create({'amount': 1})._create_payments()

        # STEP 5: ER Done (partially paid) -> Reset move to draft
        self.expense_states_employee_sheet.account_move_id.button_draft()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'post', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'draft'},
        ])

        # Re-post the move & partially pay it
        self.expense_states_employee_sheet.account_move_id.action_post()
        action_context = self.expense_states_employee_sheet.action_register_payment()['context']
        self.env['account.payment.register'].with_context(action_context).create({'amount': 1})._create_payments()

        # STEP 6: ER Done (partially paid) -> fully paid
        action_context = self.expense_states_employee_sheet.action_register_payment()['context']
        self.env['account.payment.register'].with_context(action_context).create(
            {'amount': self.expense_states_employee_sheet.amount_residual}
        )._create_payments()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'done', 'payment_state': self.paid_or_in_payment_state},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'posted', 'payment_state': self.paid_or_in_payment_state},
        ])

        # STEP 7: ER Done (fully paid) -> Reset move to draft
        self.expense_states_employee_sheet.account_move_id.button_draft()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'post', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'draft'},
        ])

        # Change the report state to a paid one
        self.expense_states_employee_sheet.account_move_id.unlink()
        self.expense_states_employee_sheet.action_sheet_move_create()
        action_context = self.expense_states_employee_sheet.action_register_payment()['context']
        payment = self.env['account.payment.register'].with_context(action_context).create({})._create_payments()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'done', 'payment_state': self.paid_or_in_payment_state},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'posted'},
        ])

        # STEP 8: ER Done (fully paid) -> Reset to draft payment (Reverts to post state)
        payment.action_draft()
        self.assertRecordValues(self.expense_states_employee_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet, [
            {'state': 'post', 'payment_state': 'not_paid'},
        ])
        self.assertRecordValues(self.expense_states_employee_sheet.account_move_id, [
            {'state': 'posted'},
        ])

    def test_expense_state_synchro_3_company_specific_flow(self):
        self.expense_states_company_sheet.action_submit_sheet()
        self.expense_states_company_sheet.approve_expense_sheets()
        self.expense_states_company_sheet.action_sheet_move_create()

        # STEP 1: ER Done & paid -> Reset move or payment to draft (nothing changes)
        self.expense_states_company_sheet.account_move_id.button_draft()
        self.assertRecordValues(self.expense_states_company_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet, [
            {'state': 'done', 'payment_state': 'paid'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet.account_move_id, [
            {'state': 'draft'},
        ])

        self.expense_states_company_sheet.account_move_id.action_post()
        self.expense_states_company_sheet.account_move_id.payment_id.action_draft()
        self.assertRecordValues(self.expense_states_company_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet, [
            {'state': 'done', 'payment_state': 'paid'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet.account_move_id, [
            {'state': 'draft'},
        ])

        # STEP 2: ER Done & paid (draft move) -> Cancel move or payment (nothing changes)
        self.expense_states_company_sheet.account_move_id.button_cancel()
        self.assertRecordValues(self.expense_states_company_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet, [
            {'state': 'done', 'payment_state': 'paid'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet.account_move_id, [
            {'state': 'cancel'},
        ])
        self.expense_states_company_sheet.account_move_id.button_draft()
        self.expense_states_company_sheet.account_move_id.payment_id.action_cancel()
        self.assertRecordValues(self.expense_states_company_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet, [
            {'state': 'done', 'payment_state': 'paid'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet.account_move_id, [
            {'state': 'cancel'},
        ])

        # Change move state to draft
        self.expense_states_company_sheet.account_move_id.button_draft()

        # STEP 3: ER draft & paid -> Delete move (Back to approve state)
        self.expense_states_company_sheet.account_move_id.unlink()
        self.assertRecordValues(self.expense_states_company_sheet.expense_line_ids, [
            {'state': 'approved'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet, [
            {'state': 'approve', 'payment_state': 'not_paid'},
        ])
        self.assertFalse(self.expense_states_company_sheet.account_move_id)

        # Re-create posted move
        self.expense_states_company_sheet.action_sheet_move_create()
        self.assertRecordValues(self.expense_states_company_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet, [
            {'payment_mode': 'company_account', 'state': 'done', 'payment_state': 'paid'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet.account_move_id, [
            {'state': 'posted'},
        ])

        # STEP 4: ER Done & paid -> Reverse move (Change payment state to 'reversed')
        self.expense_states_company_sheet.account_move_id._reverse_moves(
            default_values_list=[{'invoice_date': fields.Date.context_today(self.expense_states_company_sheet)}],
            cancel=True,
        )
        self.assertRecordValues(self.expense_states_company_sheet.expense_line_ids, [
            {'state': 'done'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet, [
            {'state': 'done', 'payment_state': 'reversed'},
        ])
        self.assertRecordValues(self.expense_states_company_sheet.account_move_id, [
            {'state': 'posted'},
        ])
