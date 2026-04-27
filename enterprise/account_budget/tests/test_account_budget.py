# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
from odoo.fields import Command
from odoo.tests import tagged
from itertools import product


@tagged('post_install', '-at_install')
class TestAccountBudget(TestAccountBudgetCommon):

    def test_account_budget(self):

        budget = self.budget_analytic_revenue

        self.assertRecordValues(budget, [{'state': 'draft'}])

        # I pressed the confirm button to confirm the Budget
        # Performing an action confirm on module budget.analytic
        budget.action_budget_confirm()

        # I check that budget is in "Confirmed" state
        self.assertRecordValues(budget, [{'state': 'confirmed'}])

        # I pressed the validate button to validate the Budget
        # Performing an action validate on module budget.analytic
        budget.action_budget_confirm()

        # I check that budget is in "Validated" state
        self.assertRecordValues(budget, [{'state': 'confirmed'}])

        # I pressed the revise button to set the Budget to "Revised" state
        # Performing an action revise on module budget.analytic
        budget.create_revised_budget()

        revised_budget = self.env['budget.analytic'].search([('parent_id', '=', budget.id)])
        self.assertTrue(revised_budget, "The revised budget should have been created")

        # I pressed the confirm button to confirm the Budget
        # Performing an action confirm on module budget.analytic
        revised_budget.action_budget_confirm()

        # I check that revised_budget is in "Confirmed" state and budget is in "Revised" state
        self.assertRecordValues(revised_budget, [{'state': 'confirmed'}])
        self.assertRecordValues(budget, [{'state': 'revised'}])

        # I pressed the done button to set the Revised Budget to "Done" state
        # Performing an action done on module budget.analytic
        revised_budget.action_budget_done()

        # I check that revised_budget is in "Done" state
        self.assertRecordValues(revised_budget, [{'state': 'done'}])

    def test_budget_split(self):
        # I created a budget split wizard with a date range and a period and a list of analytic plans
        res = self.env['budget.split.wizard'].create({
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'period': 'month',
            'analytical_plan_ids': [(6, 0, self.analytic_plan_projects.ids + self.analytic_plan_departments.ids)]
        }).action_budget_split()
        self.assertTrue(res.get('domain'), "The budget split wizard should have created and returned a domain of budget.line records")
        budget_lines = self.env['budget.line'].search(res.get('domain'))
        account_dict = {rec._column_name(): rec.account_ids.ids for rec in self.analytic_plan_projects + self.analytic_plan_departments}
        account_combinations = [dict(zip(account_dict.keys(), combination)) for combination in product(*account_dict.values())]
        for line, combination in zip(budget_lines, account_combinations):
            for column in combination:
                self.assertEqual(line[column].id, combination[column], "The budget line should have the correct accounts set")

    def test_budget_report_includes_assets(self):
        """ Test that 'asset_fixed' is included in an 'expense' budget report. """

        expense_account = self.company_data['default_account_expense']
        asset_account = self.company_data['default_account_assets']
        revenue_account = self.company_data['default_account_revenue']

        # Create a strictly "expense" budget
        budget_expense = self.env['budget.analytic'].create({
            'name': 'Test Expense Budget',
            'budget_type': 'expense',
            'date_from': '2026-01-01',
            'date_to': '2026-12-31',
        })

        budget_line_expense = self.env['budget.line'].create({
            'budget_analytic_id': budget_expense.id,
            self.project_column_name: self.analytic_account_partner_a.id,
        })

        # Generate the journal entry hitting all three accounts
        move = self.env['account.move'].create({
            'move_type': 'entry',
            'date': '2026-03-01',
            'line_ids': [
                Command.create({
                    'account_id': expense_account.id,
                    'debit': 100,
                    'analytic_distribution': {str(self.analytic_account_partner_a.id): 100},
                }),
                Command.create({
                    'account_id': asset_account.id,
                    'debit': 200,
                    'analytic_distribution': {str(self.analytic_account_partner_a.id): 100},
                }),
                Command.create({
                    'account_id': revenue_account.id,
                    'credit': 300,
                    'analytic_distribution': {str(self.analytic_account_partner_a.id): 100},
                }),
            ]
        })
        move.action_post()

        # The committed/achieved amounts should include both the expense and asset accounts: 100 + 200
        # Previously, these amounts would have been only 100 (the expense account)
        self.assertBudgetLine(budget_line_expense, committed=300, achieved=300)
