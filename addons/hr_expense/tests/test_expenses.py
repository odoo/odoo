# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged
from odoo import fields


@tagged('-at_install', 'post_install')
class TestExpenses(TestExpenseCommon):

    def test_expense_values(self):
        """ Checking accounting move entries and analytic entries when submitting expense """

        # The expense employee is able to a create an expense sheet.
        # The total should be 1725.0 because:
        # - first line: 1000.0 (unit amount) + 150.0 (tax) = 1150.0
        # - second line: (1500.0 (unit amount) + 225.0 (tax)) * 1/3 (rate) = 575.0.

        expense_sheet = self.env['hr.expense.sheet'].create({
            'name': 'First Expense for employee',
            'employee_id': self.expense_employee.id,
            'journal_id': self.company_data['default_journal_purchase'].id,
            'accounting_date': '2017-01-01',
            'expense_line_ids': [
                (0, 0, {
                    # Expense without foreign currency.
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_a.id,
                    'unit_amount': 1000.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
                    'analytic_account_id': self.analytic_account_1.id,
                    'employee_id': self.expense_employee.id,
                }),
                (0, 0, {
                    # Expense with foreign currency (rate 1:3).
                    'name': 'expense_1',
                    'date': '2016-01-01',
                    'product_id': self.product_b.id,
                    'unit_amount': 1500.0,
                    'tax_ids': [(6, 0, self.company_data['default_tax_purchase'].ids)],
                    'analytic_account_id': self.analytic_account_2.id,
                    'currency_id': self.currency_data['currency'].id,
                    'employee_id': self.expense_employee.id,
                }),
            ],
        })

        # Check expense sheet values.
        self.assertRecordValues(expense_sheet, [{'state': 'draft', 'total_amount': 1725.0}])

        expense_sheet.action_submit_sheet()
        expense_sheet.approve_expense_sheets()
        expense_sheet.action_sheet_move_create()

        # Check expense sheet journal entry values.
        self.assertRecordValues(expense_sheet.account_move_id.line_ids.sorted('balance'), [
            # Receivable line (company currency):
            {
                'debit': 0.0,
                'credit': 1150.0,
                'amount_currency': -1150.0,
                'account_id': self.company_data['default_account_payable'].id,
                'product_id': False,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': False,
            },
            # Receivable line (foreign currency):
            {
                'debit': 0.0,
                'credit': 862.5,
                'amount_currency': -1725.0,
                'account_id': self.company_data['default_account_payable'].id,
                'product_id': False,
                'currency_id': self.currency_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': False,
            },
            # Tax line (foreign currency):
            {
                'debit': 112.5,
                'credit': 0.0,
                'amount_currency': 225.0,
                'account_id': self.company_data['default_account_tax_purchase'].id,
                'product_id': False,
                'currency_id': self.currency_data['currency'].id,
                'tax_line_id': self.company_data['default_tax_purchase'].id,
                'analytic_account_id': False,
            },
            # Tax line (company currency):
            {
                'debit': 150.0,
                'credit': 0.0,
                'amount_currency': 150.0,
                'account_id': self.company_data['default_account_tax_purchase'].id,
                'product_id': False,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': self.company_data['default_tax_purchase'].id,
                'analytic_account_id': False,
            },
            # Product line (foreign currency):
            {
                'debit': 750.0,
                'credit': 0.0,
                'amount_currency': 1500.0,
                'account_id': self.company_data['default_account_expense'].id,
                'product_id': self.product_b.id,
                'currency_id': self.currency_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': self.analytic_account_2.id,
            },
            # Product line (company currency):
            {
                'debit': 1000.0,
                'credit': 0.0,
                'amount_currency': 1000.0,
                'account_id': self.company_data['default_account_expense'].id,
                'product_id': self.product_a.id,
                'currency_id': self.company_data['currency'].id,
                'tax_line_id': False,
                'analytic_account_id': self.analytic_account_1.id,
            },
        ])

        # Check expense analytic lines.
        self.assertRecordValues(expense_sheet.account_move_id.line_ids.analytic_line_ids.sorted('amount'), [
            {
                'amount': -1000.0,
                'date': fields.Date.from_string('2017-01-01'),
                'account_id': self.analytic_account_1.id,
                'currency_id': self.company_data['currency'].id,
            },
            {
                'amount': -750.0,
                'date': fields.Date.from_string('2017-01-01'),
                'account_id': self.analytic_account_2.id,
                'currency_id': self.company_data['currency'].id,
            },
        ])

    def test_expenses_with_tax_and_lockdate(self):
        ''' Test creating a journal entry for multiple expenses using taxes. A lock date is set in order to trigger
        the recomputation of the taxes base amount.
        '''
        self.env.company.tax_lock_date = '2020-02-01'

        expense = self.env['hr.expense.sheet'].create({
            'name': 'Expense for John Smith',
            'employee_id': self.expense_employee.id,
            'accounting_date': '2020-01-01'
        })

        for i in range(2):
            expense_line = self.env['hr.expense'].create({
                'name': 'Car Travel Expenses',
                'employee_id': self.expense_employee.id,
                'product_id': self.product_a.id,
                'unit_amount': 350.00,
                'tax_ids': [(6, 0, [self.tax_purchase_a.id])],
                'sheet_id': expense.id,
                'analytic_account_id': self.analytic_account_1.id,
            })
            expense_line._onchange_product_id_date_account_id()

        expense.action_submit_sheet()
        expense.approve_expense_sheets()

        # Assert not "Cannot create unbalanced journal entry" error.
        expense.action_sheet_move_create()
