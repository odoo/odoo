# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.exceptions import AccessError, UserError
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestExpensesAccessRights(TestExpenseCommon):

    def test_expense_access_rights(self):
        ''' The expense employee can't be able to create an expense for someone else.'''

        expense_employee_2 = self.env['hr.employee'].create({
            'name': 'expense_employee_2',
            'user_id': self.env.user.id,
            'work_contact_id': self.env.user.partner_id.id,
            'address_id': self.env.user.partner_id.id,
        })

        with self.assertRaises(AccessError):
            self.env['hr.expense'].with_user(self.expense_user_employee).create({
                'name': "Superboy costume washing",
                'employee_id': expense_employee_2.id,
                'product_id': self.product_a.id,
                'quantity': 1,
                'unit_amount': 1,
            })

    def test_expense_sheet_access_rights_approve(self):

        # The expense employee is able to a create an expense sheet.

        expense_sheet = self.env['hr.expense.sheet'].with_user(self.expense_user_employee).create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                (0, 0, {
                    # Expense without foreign currency but analytic account.
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 1000.0,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })
        self.env.flush_all()

        self.assertRecordValues(expense_sheet, [{'state': 'draft'}])

        # The expense employee is able to submit the expense sheet.

        expense_sheet.with_user(self.expense_user_employee).action_submit_sheet()
        self.assertRecordValues(expense_sheet, [{'state': 'submit'}])

        # The expense employee is not able to approve itself the expense sheet.

        with self.assertRaises(UserError):
            expense_sheet.with_user(self.expense_user_employee).action_approve_expense_sheets()
        self.assertRecordValues(expense_sheet, [{'state': 'submit'}])

        # An expense manager is required for this step.

        expense_sheet.with_user(self.expense_user_manager).action_approve_expense_sheets()
        self.assertRecordValues(expense_sheet, [{'state': 'approve'}])

        # An expense manager is not able to create the journal entry.

        with self.assertRaises(AccessError):
            expense_sheet.with_user(self.expense_user_manager).action_sheet_move_create()
        self.assertRecordValues(expense_sheet, [{'state': 'approve'}])

        # An expense manager having accounting access rights is able to create the journal entry.

        expense_sheet.with_user(self.env.user).action_sheet_move_create()
        self.assertRecordValues(expense_sheet, [{'state': 'post'}])

    def test_expense_sheet_access_rights_refuse(self):

        # The expense employee is able to a create an expense sheet.

        expense_sheet = self.env['hr.expense.sheet'].with_user(self.expense_user_employee).create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                (0, 0, {
                    # Expense without foreign currency but analytic account.
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 1000.0,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })
        self.assertRecordValues(expense_sheet, [{'state': 'draft'}])

        # The expense employee is able to submit the expense sheet.

        expense_sheet.with_user(self.expense_user_employee).action_submit_sheet()
        self.assertRecordValues(expense_sheet, [{'state': 'submit'}])

        # The expense employee is not able to refuse itself the expense sheet.

        with self.assertRaises(UserError):
            expense_sheet.with_user(self.expense_user_employee).action_refuse_expense_sheets()
        self.assertRecordValues(expense_sheet, [{'state': 'submit'}])

        # An expense manager is required for this step.

        expense_sheet.with_user(self.expense_user_manager).action_refuse_expense_sheets()
        expense_sheet.with_user(self.expense_user_manager)._do_refuse('failed')
        self.assertRecordValues(expense_sheet, [{'state': 'cancel'}])
