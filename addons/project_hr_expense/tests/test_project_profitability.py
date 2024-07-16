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

        expense_sheet.action_approve_expense_sheets()
        self.assertEqual(expense_sheet.state, 'approve')
        return expense_sheet


@tagged('post_install', '-at_install')
class TestProjectHrExpenseProfitability(TestProjectProfitabilityCommon, TestProjectHrExpenseProfitabilityCommon):

    def test_project_profitability(self):
        self.project.company_id = False
        # Create a new company with the foreign currency.
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency
        foreign_employee = self.env['hr.employee'].create({
            'name': 'Foreign employee',
            'company_id': foreign_company.id,
            'work_email': 'email@email',
        })

        expense = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 350.00,
            'company_id': self.env.company.id,
            'analytic_distribution': {self.project.account_id.id: 100},
        })

        expense_sheet = self.check_project_profitability_before_creating_and_approving_expense_sheet(
            expense,
            self.project,
            self.project_profitability_items_empty)
        self.assertEqual(expense_sheet.state, 'approve')

        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('expenses', sequence_per_invoice_type)
        expense_sequence = sequence_per_invoice_type['expenses']

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the sheets are not posted or done.',
        )

        # Create an expense in a foreign company, the expense is linked to the AA of the project.
        expense_foreign = self.env['hr.expense'].create({
            'name': 'Car Travel Expenses foreign',
            'employee_id': foreign_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 350.00,
            'company_id': foreign_company.id,
            'analytic_distribution': {self.project.account_id.id: 100},
            'currency_id': self.foreign_currency.id,
        })
        expense_sheet_vals_list = expense_foreign._get_default_expense_sheet_values()
        expense_sheet_vals_list[0]['employee_journal_id'] = self.company_data_2['default_journal_purchase'].id
        expense_sheet_foreign = self.env['hr.expense.sheet'].create(expense_sheet_vals_list)
        expense_sheet_foreign.action_submit_sheet()
        self.assertEqual(expense_sheet_foreign.state, 'submit')
        expense_sheet_foreign.action_approve_expense_sheets()
        self.assertEqual(expense_sheet_foreign.state, 'approve')
        expense_sheet_foreign.action_sheet_move_post()
        self.assertEqual(expense_sheet_foreign.state, 'post')
        expense_sheet.action_sheet_move_post()
        self.assertEqual(expense_sheet.state, 'post')

        # Both costs should now be computed in the project profitability, since both expense sheets were posted
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'costs': {
                    'data': [{
                        'id': 'expenses',
                        'sequence': expense_sequence,
                        'to_bill': 0.0,
                        'billed': -expense.untaxed_amount_currency - expense_foreign.untaxed_amount_currency * 0.2
                    }],
                    'total': {'to_bill': 0.0, 'billed': -expense.untaxed_amount_currency - expense_foreign.untaxed_amount_currency * 0.2},
                },
                'revenues': {'data': [], 'total': {'to_invoice': 0.0, 'invoiced': 0.0}},
            },
        )

        # Reset to draft the expense sheet of the main company. Only the total from the foreign company should be computed
        expense_sheet.action_reset_expense_sheets()
        self.assertEqual(expense_sheet.state, 'draft')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'costs': {
                    'data': [{'id': 'expenses', 'sequence': expense_sequence, 'to_bill': 0.0, 'billed': -expense_foreign.untaxed_amount_currency * 0.2}],
                    'total': {'to_bill': 0.0, 'billed': -expense_foreign.untaxed_amount_currency * 0.2},
                },
                'revenues': {'data': [], 'total': {'to_invoice': 0.0, 'invoiced': 0.0}},
            },
        )

        # Reset to draft the expense sheet of the foreign company. No data should be computed now.
        expense_sheet_foreign.action_reset_expense_sheets()
        self.assertEqual(expense_sheet_foreign.state, 'draft')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the sheets are not posted or done.',
        )

    def test_project_profitability_after_expense_sheet_actions(self):
        expense = self.env["hr.expense"].create(
            {
                "name": "Car Travel Expenses",
                "employee_id": self.expense_employee.id,
                "product_id": self.product_c.id,
                "total_amount": 50.00,
                "company_id": self.project.company_id.id,
                "analytic_distribution": {self.project.account_id.id: 100},
            }
        )
        expense_sheet = self.env["hr.expense.sheet"].create(
            {
                "name": "Expense for Jannette",
                "employee_id": self.expense_employee.id,
                "expense_line_ids": expense,
            }
        )

        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('expenses', sequence_per_invoice_type)
        expense_sequence = sequence_per_invoice_type['expenses']

        expense_sheet.action_submit_sheet()
        expense_sheet.action_approve_expense_sheets()
        expense_sheet.action_sheet_move_post()

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            {
                'costs': {
                    'data': [{'id': 'expenses', 'sequence': expense_sequence, 'to_bill': 0.0, 'billed': -expense.untaxed_amount_currency}],
                    'total': {'to_bill': 0.0, 'billed': -expense.untaxed_amount_currency},
                },
                'revenues': {'data': [], 'total': {'to_invoice': 0.0, 'invoiced': 0.0}},
            },
        )
