# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import Command
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestExpenseMultiCompany(TestExpenseCommon):

    def test_expense_sheet_multi_company(self):
        self.expense_employee.company_id = self.company_data_2['company']

        # The expense employee is able to a create an expense sheet for company_2.
        # product_a needs a standard_price in company_2
        self.product_a.with_context(allowed_company_ids=self.company_data_2['company'].ids).standard_price = 100

        expense_sheet_approve = self.env['hr.expense.sheet'] \
            .with_user(self.expense_user_employee) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            .create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data_2['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [Command.create({
                # Expense without foreign currency but analytic account.
                'name': 'expense_1',
                'date': '2016-01-01',
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'employee_id': self.expense_employee.id,
            })],
        })
        expense_sheet_refuse = self.env['hr.expense.sheet'] \
            .with_user(self.expense_user_employee) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            .create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data_2['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [Command.create({
                # Expense without foreign currency but analytic account.
                'name': 'expense_1',
                'date': '2016-01-01',
                'product_id': self.product_a.id,
                'price_unit': 1000.0,
                'employee_id': self.expense_employee.id,
            })],
        })
        expenses = expense_sheet_approve | expense_sheet_refuse
        self.assertRecordValues(expenses, [
            {'company_id': self.company_data_2['company'].id},
            {'company_id': self.company_data_2['company'].id},
        ])

        # The expense employee is able to submit the expense sheet.
        expenses.with_user(self.expense_user_employee).action_submit_sheet()

        # An expense manager is not able to approve nor refuse without access to company_2.
        with self.assertRaises(UserError):
            expense_sheet_approve \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=self.company_data['company'].ids) \
                .action_approve_expense_sheets()

        with self.assertRaises(UserError):
            expense_sheet_refuse \
                .with_user(self.expense_user_manager) \
                .with_context(allowed_company_ids=self.company_data['company'].ids) \
                ._do_refuse('failed')

        # An expense manager is able to approve/refuse with access to company_2.
        expense_sheet_approve \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            .action_approve_expense_sheets()
        expense_sheet_refuse \
            .with_user(self.expense_user_manager) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            ._do_refuse('failed')

        # An expense manager having accounting access rights is not able to create the journal entry without access
        # to company_2.
        with self.assertRaises(UserError):
            expense_sheet_approve \
                .with_user(self.env.user) \
                .with_context(allowed_company_ids=self.company_data['company'].ids) \
                .action_sheet_move_create()

        # An expense manager having accounting access rights is able to create the journal entry with access to
        # company_2.
        expense_sheet_approve \
            .with_user(self.env.user) \
            .with_context(allowed_company_ids=self.company_data_2['company'].ids) \
            .action_sheet_move_create()
