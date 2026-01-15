# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.addons.project.tests.test_project_profitability import TestProjectProfitabilityCommon
from odoo.tests.common import tagged


class TestProjectHrExpenseProfitabilityCommon(TestExpenseCommon):
    def check_project_profitability_before_creating_and_approving_expense(self, expense, project, project_profitability_items_empty):
        self.assertDictEqual(
            project._get_profitability_items(False),
            project_profitability_items_empty,
            'No data should be found since the expense is not approved yet.',
        )

        expense.action_submit()
        self.assertDictEqual(
            project._get_profitability_items(False),
            project_profitability_items_empty,
            'No data should be found since the expense is not approved yet.',
        )
        expense.action_approve()
        return expense


@tagged('post_install', '-at_install')
class TestProjectHrExpenseProfitability(TestProjectProfitabilityCommon, TestProjectHrExpenseProfitabilityCommon):

    def test_project_profitability(self):
        self.project.company_id = False
        # Create a new company with the foreign currency.
        foreign_company = self.company_data_2['company']
        foreign_company.currency_id = self.foreign_currency
        foreign_employee = self.env['hr.employee'].sudo().create({
            'name': 'Foreign employee',
            'company_id': foreign_company.id,
            'expense_manager_id': self.expense_user_manager.id,
            'work_email': 'email@email',
        })

        expense = self.create_expenses({
            'name': 'Car Travel Expenses',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 350.00,
            'company_id': self.env.company.id,
            'analytic_distribution': {self.project.account_id.id: 100},
        })

        self.check_project_profitability_before_creating_and_approving_expense(
            expense,
            self.project,
            self.project_profitability_items_empty)
        self.assertEqual(expense.state, 'approved')

        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('expenses', sequence_per_invoice_type)
        expense_sequence = sequence_per_invoice_type['expenses']

        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the expenses are not posted.',
        )

        # Create an expense in a foreign company, the expense is linked to the AA of the project.
        expense_foreign = self.create_expenses({
            'name': 'Car Travel Expenses foreign',
            'employee_id': foreign_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 350.00,
            'company_id': foreign_company.id,
            'analytic_distribution': {self.project.account_id.id: 100},
            'currency_id': self.foreign_currency.id,
        })
        expense_foreign.action_submit()
        self.assertEqual(expense_foreign.state, 'submitted')
        expense_foreign.action_approve()
        self.assertEqual(expense_foreign.state, 'approved')
        self.post_expenses_with_wizard(expense_foreign.with_company(foreign_company))
        self.assertEqual(expense_foreign.state, 'posted')
        self.post_expenses_with_wizard(expense)
        self.assertEqual(expense.state, 'posted')

        # Both costs should now be computed in the project profitability, since both expenses were posted
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

        # Reset to approved the expense of the main company. Only the total from the foreign company should be computed
        expense.account_move_id.button_draft()
        expense.account_move_id.unlink()
        self.assertEqual(expense.state, 'approved')
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

        # Reset to approved the expense of the foreign company. No data should be computed now.
        expense_foreign.account_move_id.button_draft()
        expense_foreign.account_move_id.unlink()
        self.assertEqual(expense_foreign.state, 'approved')
        self.assertDictEqual(
            self.project._get_profitability_items(False),
            self.project_profitability_items_empty,
            'No data should be found since the sheets are not posted or done.',
        )

    def test_project_profitability_after_expense_actions(self):
        expense = self.create_expenses({
            "name": "Car Travel Expenses",
            "total_amount": 50.00,
            "company_id": self.project.company_id.id,
            "analytic_distribution": {self.project.account_id.id: 100},
        })

        sequence_per_invoice_type = self.project._get_profitability_sequence_per_invoice_type()
        self.assertIn('expenses', sequence_per_invoice_type)
        expense_sequence = sequence_per_invoice_type['expenses']

        expense.action_submit()
        expense.action_approve()
        self.post_expenses_with_wizard(expense)

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
