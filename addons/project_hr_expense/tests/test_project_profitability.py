# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon
from odoo.tests.common import tagged


class TestProjectHrExpenseProfitabilityCommon(TestExpenseCommon):
    def check_project_profitability_before_creating_and_approving_expense_sheet(self, expense, project, project_profitability_items_empty):
        self.assertDictEqual(
            project._get_profitability_items(False),
            project_profitability_items_empty,
            'No data should be found since the expense is not approved yet.',
        )

        expense_sheet_vals_list = expense._get_default_expense_sheet_values()
        expense_sheet = self.env['hr.expense.sheet'].create(expense_sheet_vals_list)
        self.assertEqual(len(expense_sheet), 1, '1 expense sheet should be created.')

        expense_sheet.action_submit_sheet()
        self.assertEqual(expense_sheet.state, 'submit')

        self.assertDictEqual(
            project._get_profitability_items(False),
            project_profitability_items_empty,
            'No data should be found since the sheet is not approved yet.',
        )

        expense_sheet.approve_expense_sheets()
        self.assertEqual(expense_sheet.state, 'approve')
        return expense_sheet


@tagged('post_install', '-at_install')
class TestProjectHrExpenseProfitability(TestProjectProfitabilityCommon, TestProjectHrExpenseProfitabilityCommon):

    def test_project_profitability(self):
        expense = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
            'unit_amount': 350.00,
            'company_id': self.project.company_id.id,
            'analytic_distribution': {self.project.analytic_account_id.id: 100},
        })

        expense_sheet = self.check_project_profitability_before_creating_and_approving_expense_sheet(
            expense,
            self.project,
            self.project_profitability_items_empty)

        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('expenses', sequence_per_invoice_type)
        expense_sequence = sequence_per_invoice_type['expenses']

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'costs': {
                    'data': [{'id': 'expenses', 'sequence': expense_sequence, 'to_bill': 0.0, 'billed': -expense.untaxed_amount}],
                    'total': {'to_bill': 0.0, 'billed': -expense.untaxed_amount},
                },
                'revenues': {'data': [], 'total': {'to_invoice': 0.0, 'invoiced': 0.0}},
            },
        )

        expense_sheet.refuse_sheet('Test cancel expense')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the sheet is not approved yet.',
        )
