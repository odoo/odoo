# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged
from odoo.exceptions import UserError


@tagged('post_install', '-at_install')
class TestExpenseMultiCompany(TestExpenseCommon):

    def test_expense_sheet_multi_company_approve(self):
        self.expense_employee.company_id = self.company_data_2['company']

        # The expense employee is able to a create an expense sheet for company_2.

        expense_sheet = self.env['hr.expense.sheet']\
            .with_user(self.expense_user_employee)\
            .with_context(allowed_company_ids=self.company_data_2['company'].ids)\
            .create({
                'name': 'First Expense for employee',
                'employee_id': self.expense_employee.id,
                'journal_id': self.company_data_2['default_journal_purchase'].id,
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
        self.assertRecordValues(expense_sheet, [{'company_id': self.company_data_2['company'].id}])

        # The expense employee is able to submit the expense sheet.

        expense_sheet.with_user(self.expense_user_employee).action_submit_sheet()

        # An expense manager is not able to approve without access to company_2.

        with self.assertRaises(UserError):
            expense_sheet\
                .with_user(self.expense_user_manager)\
                .with_context(allowed_company_ids=self.company_data['company'].ids)\
                .approve_expense_sheets()

        # An expense manager is able to approve with access to company_2.

        expense_sheet\
            .with_user(self.expense_user_manager)\
            .with_context(allowed_company_ids=self.company_data_2['company'].ids)\
            .approve_expense_sheets()

        # An expense manager having accounting access rights is not able to create the journal entry without access
        # to company_2.

        with self.assertRaises(UserError):
            expense_sheet\
                .with_user(self.env.user)\
                .with_context(allowed_company_ids=self.company_data['company'].ids)\
                .action_sheet_move_create()

        # An expense manager having accounting access rights is able to create the journal entry with access to
        # company_2.

        expense_sheet\
            .with_user(self.env.user)\
            .with_context(allowed_company_ids=self.company_data_2['company'].ids)\
            .action_sheet_move_create()

    def test_expense_sheet_multi_company_refuse(self):
        self.expense_employee.company_id = self.company_data_2['company']

        # The expense employee is able to a create an expense sheet for company_2.

        expense_sheet = self.env['hr.expense.sheet']\
            .with_user(self.expense_user_employee)\
            .with_context(allowed_company_ids=self.company_data_2['company'].ids)\
            .create({
                'name': 'First Expense for employee',
                'employee_id': self.expense_employee.id,
                'journal_id': self.company_data_2['default_journal_purchase'].id,
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
        self.assertRecordValues(expense_sheet, [{'company_id': self.company_data_2['company'].id}])

        # The expense employee is able to submit the expense sheet.

        expense_sheet.with_user(self.expense_user_employee).action_submit_sheet()

        # An expense manager is not able to approve without access to company_2.

        with self.assertRaises(UserError):
            expense_sheet\
                .with_user(self.expense_user_manager)\
                .with_context(allowed_company_ids=self.company_data['company'].ids)\
                .refuse_sheet('')

        # An expense manager is able to approve with access to company_2.

        expense_sheet\
            .with_user(self.expense_user_manager)\
            .with_context(allowed_company_ids=self.company_data_2['company'].ids)\
            .refuse_sheet('')
