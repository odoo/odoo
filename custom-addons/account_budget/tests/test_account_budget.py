# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
from odoo import Command
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestAccountBudget(TestAccountBudgetCommon):

    def test_account_budget(self):

        # Creating a crossovered.budget record
        budget = self.env['crossovered.budget'].create({
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'name': 'Budget 2019',
            'state': 'draft'
        })

        # I created two different budget lines
        # Modifying a crossovered.budget record
        self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': budget.id,
            'analytic_account_id': self.analytic_account_partner_b.id,
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'general_budget_id': self.account_budget_post_purchase0.id,
            'planned_amount': 10000.0,
        })
        self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': budget.id,
            'analytic_account_id': self.analytic_account_partner_a_2.id,
            'date_from': '2019-09-01',
            'date_to': '2019-09-30',
            'general_budget_id': self.account_budget_post_sales0.id,
            'planned_amount': 400000.0,
        })

        self.assertRecordValues(budget, [{'state': 'draft'}])

        # I pressed the confirm button to confirm the Budget
        # Performing an action confirm on module crossovered.budget
        budget.action_budget_confirm()

        # I check that budget is in "Confirmed" state
        self.assertRecordValues(budget, [{'state': 'confirm'}])

        # I pressed the validate button to validate the Budget
        # Performing an action validate on module crossovered.budget
        budget.action_budget_validate()

        # I check that budget is in "Validated" state
        self.assertRecordValues(budget, [{'state': 'validate'}])

        # I pressed the done button to set the Budget to "Done" state
        # Performing an action done on module crossovered.budget
        budget.action_budget_done()

        # I check that budget is in "done" state
        self.assertRecordValues(budget, [{'state': 'done'}])

    def test_practical_amount(self):
        general_accounts = self.env['account.account'].search([('company_id', '=', self.env.company.id)], limit=2)
        _project_plan, other_plans = self.env['account.analytic.plan']._get_all_plans()
        analytic = self.env['account.analytic.account'].create({'name': 'R&D', 'plan_id': other_plans[0].id})
        budget_position = self.env['account.budget.post'].create({
            'name': 'R&D',
            'account_ids': [Command.set(general_accounts[0].ids)],
        })
        budget = self.env['crossovered.budget'].create({
            'date_from': '2019-01-01',
            'date_to': '2019-12-31',
            'name': 'Budget 2019',
            'state': 'draft',
            'crossovered_budget_line': [
                Command.create({
                    'date_from': '2019-01-01',
                    'date_to': '2019-12-31',
                    'analytic_account_id': analytic.id,
                    'general_budget_id': budget_position.id,
                    'planned_amount': 10000.0,
                }),
                Command.create({
                    'date_from': '2019-01-01',
                    'date_to': '2019-12-31',
                    'general_budget_id': budget_position.id,
                    'planned_amount': 10000.0,
                }),
                Command.create({
                    'date_from': '2019-01-01',
                    'date_to': '2019-12-31',
                    'analytic_account_id': analytic.id,
                    'planned_amount': 10000.0,
                }),
            ],
        })
        with_all, with_position, with_analytic = budget.crossovered_budget_line

        self.assertEqual(with_all.practical_amount, 0)
        self.assertEqual(with_position.practical_amount, 0)
        self.assertEqual(with_position.practical_amount, 0)

        move = self.env['account.move'].create({
            'date': '2019-01-01',
            'line_ids': [
                Command.create({
                    'name': '1',
                    'credit': 100,
                    'account_id': general_accounts[0].id,
                    'analytic_distribution': {analytic.id: 100},
                }),
                Command.create({
                    'name': '2',
                    'credit': 200,
                    'account_id': general_accounts[0].id
                }),
                Command.create({
                    'name': '3',
                    'debit': 300,
                    'account_id': general_accounts[1].id
                }),
            ]
        })
        move.action_post()
        self.env['account.analytic.line'].create([{
            'auto_account_id': analytic.id,
            'date': '2019-01-01',
            'name': '1',
            'amount': 50,
        }])

        self.env['crossovered.budget.lines'].invalidate_model(['practical_amount'])
        self.assertEqual(with_all.practical_amount, 100,
                         "Only the line linked to both an analytic and a general account should be accounted")
        self.assertEqual(with_position.practical_amount, 300,
                         "Both lines using the general account should be accounted")
        self.assertEqual(with_analytic.practical_amount, 150,
                         "Both lines using the analytic account should be accounted")
