# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.hr_expense.tests.common import TestExpenseCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestExpenseAnalytics(TestExpenseCommon):

    def test_company_paid_expense_analytic_on_pnl_line_only(self):
        """ Tests that the analytic distribution must only be on the P&L (expense) line """
        project = self.env['project.project'].sudo().create({'name': 'Expense Project'})
        project._create_analytic_account()
        distribution = project._get_analytic_distribution()
        self.assertTrue(distribution, "The project must expose an analytic distribution to reproduce the bug")

        # Mimic the Project overview action which injects project_id in the context
        expense = self.env['hr.expense'].with_context(project_id=project.id).create({
            'name': 'Company paid expense from project',
            'employee_id': self.expense_employee.id,
            'product_id': self.product_c.id,
            'total_amount_currency': 1000.0,
            'payment_mode': 'company_account',
            'company_id': self.company_data['company'].id,
        })
        self.assertEqual(
            expense.analytic_distribution,
            distribution,
            "The expense should inherit the analytic distribution from the project context",
        )

        expense.action_submit()
        expense.action_approve()
        expense.action_post()

        move = expense.account_move_id
        self.assertTrue(move, "Posting a company-paid expense should create a payment move")

        pnl_lines = move.line_ids.filtered(lambda line: line.account_type == 'expense')
        other_lines = move.line_ids - pnl_lines
        self.assertTrue(pnl_lines, "The move should contain the expense (P&L) line")
        self.assertTrue(other_lines, "The move should contain the outstanding/tax lines")

        for line in pnl_lines:
            self.assertEqual(
                line.analytic_distribution,
                distribution,
                "The analytic distribution should stay on the expense (P&L) line",
            )
        for line in other_lines:
            self.assertFalse(
                line.analytic_distribution,
                "The project analytic distribution must not leak onto the outstanding/tax lines",
            )
