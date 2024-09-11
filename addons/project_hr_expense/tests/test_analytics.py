# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_expense.tests.common import TestExpenseCommon


class TestAnalytics(TestExpenseCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.project_plan, _other_plans = cls.env['account.analytic.plan']._get_all_plans()
        cls.analytic_account1, cls.analytic_account2 = cls.env['account.analytic.account'].create([
            {
                'name': 'Account 1',
                'plan_id': cls.project_plan.id,
            },
            {
                'name': 'Account 2',
                'plan_id': cls.project_plan.id,
            },
        ])
        cls.project = cls.env['project.project'].create({
            'name': 'Project',
            'account_id': cls.analytic_account1.id,
        })

    def test_project_analytics_to_expense(self):
        expense = self.env['hr.expense'].with_context(project_id=self.project.id).create({
            'name': 'Expense',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_a.id,
        })
        self.assertEqual(
            expense.analytic_distribution,
            {str(self.analytic_account1.id): 100},
            "The analytic distribution of the created expense should be set to the account of the project specified in the context.",
        )
        self.project.account_id = self.analytic_account2
        expense.analytic_distribution = False
        expense.with_context(project_id=self.project.id)._compute_analytic_distribution()
        self.assertEqual(
            expense.analytic_distribution,
            {str(self.analytic_account2.id): 100},
            "The analytic distribution of the expense should be set to the account of the project specified in the context.",
        )
