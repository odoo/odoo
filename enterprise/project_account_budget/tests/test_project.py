# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import lxml

from datetime import date
from dateutil.relativedelta import relativedelta

from odoo import Command
from odoo.addons.project.tests.test_project_base import TestProjectCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestProject(TestProjectCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.analytic_plan = cls.env['account.analytic.plan'].create({
            'name': 'Plan',
        })

        cls.analytic_account = cls.env['account.analytic.account'].create({
            'name': 'Project - AA',
            'code': 'AA-1234',
            'plan_id': cls.analytic_plan.id,
        })
        cls.project_goats.write({
            'account_id': cls.analytic_account.id,
        })

    def test_get_budget_items_expense(self):
        """
        Check budget items data with expense budget only
        """
        if not self.project_pigs.account_id:
            self.assertEqual(self.project_pigs._get_budget_items(False), None, 'No budget should be return since no AA is set into the project.')
        self.assertTrue(self.env.user.has_group('analytic.group_analytic_accounting'))
        self.assertDictEqual(
            self.project_goats._get_budget_items(False),
            {
                'data': [],
                'total': {'allocated': 0, 'progress': 0, 'spent': 0},
                'can_add_budget': False,
            },
            'No budget has been created for this project.'
        )

        self.assertEqual(self.project_goats.account_id, self.analytic_account, 'The project and budget line will use the same analytic account on the same plan.')
        plan_fname = self.analytic_account.plan_id._column_name()
        today = date.today()
        budget_1 = self.env['budget.analytic'].create({
            'name': 'Project Goats Expense Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'expense',
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account.id,
                'budget_amount': 500,
            })],
        })
        budget_1.action_budget_confirm()

        budget_items = self.project_goats._get_budget_items(False)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500.0,
                    'budgets': [],
                    'budget_type': 'expense',
                    'progress': 1.0,
                    'spent': 0.0,
                },
            ],
            'total': {'allocated': -500.0, 'spent': 0.0, 'progress': 1.0},
            'can_add_budget': False,
        })

    def test_get_budget_items_revenue(self):
        """
        Check budget items data with revenue budget only
        """
        self.assertEqual(self.project_goats.account_id, self.analytic_account, 'The project and budget line will use the same analytic account on the same plan.')
        plan_fname = self.analytic_account.plan_id._column_name()
        today = date.today()
        budget_1 = self.env['budget.analytic'].create({
            'name': 'Project Goats Revenue 1 Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'revenue',
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account.id,
                'budget_amount': 500,
            })],
        })
        budget_1.action_budget_confirm()

        budget_items = self.project_goats._get_budget_items(False)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500.0,
                    'budgets': [],
                    'budget_type': 'revenue',
                    'progress': -1.0,
                    'spent': 0.0,
                },
            ],
            'total': {'allocated': 500.0, 'spent': 0.0, 'progress': -1.0},
            'can_add_budget': False,
        })

    def test_get_budget_items_both(self):
        """
        Check budget items data with both budget only
        """
        self.assertEqual(self.project_goats.account_id, self.analytic_account, 'The project and budget line will use the same analytic account on the same plan.')
        plan_fname = self.analytic_account.plan_id._column_name()
        today = date.today()
        budget_1 = self.env['budget.analytic'].create({
            'name': 'Project Goats Both Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'both',
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account.id,
                'budget_amount': 500,
            })],
        })
        budget_1.action_budget_confirm()

        budget_items = self.project_goats._get_budget_items(False)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500.0,
                    'budgets': [],
                    'budget_type': 'both',
                    'progress': -1.0,
                    'spent': 0.0,
                },
            ],
            'total': {'allocated': 500.0, 'spent': 0.0, 'progress': -1.0},
            'can_add_budget': False,
        })

    def test_get_budget_items_expense_and_revenue(self):
        """
        Check budget items data with expense and revenue budgets
        """
        self.assertEqual(self.project_goats.account_id, self.analytic_account, 'The project and budget line will use the same analytic account on the same plan.')
        plan_fname = self.analytic_account.plan_id._column_name()
        today = date.today()
        budget_1 = self.env['budget.analytic'].create({
            'name': 'Project Goats Expense Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'expense',
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account.id,
                'budget_amount': 500,
            })],
        })
        budget_1.action_budget_confirm()

        budget_2 = self.env['budget.analytic'].create({
            'name': 'Project Goats Revenue Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'revenue',
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account.id,
                'budget_amount': 1500,
            })],
        })
        budget_2.action_budget_confirm()

        budget_items = self.project_goats._get_budget_items(False)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        del budget_items['data'][1]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][1]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500.0,
                    'budgets': [],
                    'budget_type': 'expense',
                    'progress': 1.0,
                    'spent': 0.0,
                },
                {
                    'allocated': 1500.0,
                    'budgets': [],
                    'budget_type': 'revenue',
                    'progress': -1.0,
                    'spent': 0.0,
                },
            ],
            'total': {'allocated': 1000.0, 'spent': 0.0, 'progress': -1.0},
            'can_add_budget': False,
        })

        self.analytic_plan_pigs = self.env['account.analytic.plan'].create({
            'name': 'Plan pigs',
        })

        self.analytic_account_pigs = self.env['account.analytic.account'].create({
            'name': 'Project pigs -  AA',
            'code': 'AA-1234',
            'plan_id': self.analytic_plan_pigs.id,
        })
        self.project_pigs.write({
            'account_id': self.analytic_account_pigs.id,
        })

        self.assertEqual(self.project_pigs.account_id, self.analytic_account_pigs, 'The project and budget line will use the same analytic account on the same plan.')
        plan_fname = self.analytic_account_pigs.plan_id._column_name()
        budget_1 = self.env['budget.analytic'].create({
            'name': 'Project Pigs Expense Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'expense',
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account_pigs.id,
                'budget_amount': 1500,
            })],
        })
        budget_1.action_budget_confirm()

        plan_fname = self.analytic_account_pigs.plan_id._column_name()
        budget_2 = self.env['budget.analytic'].create({
            'name': 'Project Pigs Revenue Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'revenue',
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account_pigs.id,
                'budget_amount': 500,
            })],
        })
        budget_2.action_budget_confirm()

        budget_items = self.project_pigs._get_budget_items(False)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        del budget_items['data'][1]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][1]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 1500.0,
                    'budgets': [],
                    'budget_type': 'expense',
                    'progress': 1.0,
                    'spent': 0.0,
                },
                {
                    'allocated': 500.0,
                    'budgets': [],
                    'budget_type': 'revenue',
                    'progress': -1.0,
                    'spent': 0.0,
                },
            ],
            'total': {'allocated': -1000.0, 'spent': 0.0, 'progress': 1.0},
            'can_add_budget': False,
        })

    def test_get_budget_items_with_action(self):
        self.assertEqual(self.project_goats.account_id, self.analytic_account, 'The project and budget line will use the same analytic account on the same plan.')
        plan_fname = self.analytic_account.plan_id._column_name()
        today = date.today()
        budgets = self.env['budget.analytic']
        for budget_name, planned_amount in [
            ('Project Goats Budget', 500),
            ('Project Pigs Budget', 1000),
        ]:
            budget = self.env['budget.analytic'].create({
                'name': budget_name,
                'date_from': today.replace(day=1),
                'date_to': today + relativedelta(months=1, days=-1),
                'budget_line_ids': [
                    Command.create({
                        plan_fname: self.analytic_account.id,
                        'budget_amount': planned_amount,
                    }),
                ],
            })
            budget.action_budget_confirm()
            budgets += budget

        self.env.user.groups_id += self.env.ref('account.group_account_user')
        self.assertTrue(self.env.user.has_group('analytic.group_analytic_accounting'))
        budget_items = self.project_goats.with_context({'allowed_company_ids': [self.env.company.id]})._get_budget_items(with_action=True)
        del budget_items['data'][0]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][0]['id']
        del budget_items['data'][1]['name']  # remove the name because it is a lazy translation.
        del budget_items['data'][1]['id']
        self.assertDictEqual(budget_items, {
            'data': [
                {
                    'allocated': 500.0,
                    'progress': 1.0,
                    'spent': 0.0,
                    'budgets': [],
                    'budget_type': 'expense',
                    'action': {
                        'name': 'action_view_budget_lines',
                        'type': 'object',
                        'args': f'[[["id", "in", {budgets[0].budget_line_ids.ids}]]]',
                    }
                },
                {
                    'allocated': 1000.0,
                    'progress': 1.0,
                    'spent': 0.0,
                    'budgets': [],
                    'budget_type': 'expense',
                    'action': {
                        'name': 'action_view_budget_lines',
                        'type': 'object',
                        'args': f'[[["id", "in", {budgets[1].budget_line_ids.ids}]]]',
                    }
                },
            ],
            'total': {'allocated': -1500.0, 'spent': 0.0, 'progress': 1.0},
            'form_view_id': self.env.ref('project_account_budget.view_budget_analytic_form_dialog').id,
            'can_add_budget': True,
            'company_id': self.env.company.id,
        })

    def test_get_budget_items_plans_mismatch(self):
        self.assertTrue(self.env.user.has_group('analytic.group_analytic_accounting'))
        self.assertEqual(self.project_goats.account_id, self.analytic_account, 'The project and budget line will use the same analytic account.')
        analytic_plan_2 = self.env['account.analytic.plan'].create({
            'name': 'Plan 2',
        })
        self.assertNotEqual(self.project_goats.account_id.plan_id, analytic_plan_2, 'The project account and budget line will use different analytic plans.')
        plan_fname = analytic_plan_2._column_name()
        today = date.today()
        budget = self.env['budget.analytic'].create({
            'name': 'Project Goats Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_line_ids': [Command.create({
                plan_fname: self.analytic_account.id,
                'budget_amount': 500,
            })],
        })
        budget.action_budget_confirm()
        self.assertDictEqual(
            self.project_goats._get_budget_items(False),
            {
                'data': [],
                'total': {'allocated': 0, 'progress': 0, 'spent': 0},
                'can_add_budget': False,
            },
            'No budget has been created for this project. Because the plan of the budget line does not match the plan of the account of the project.'
        )

    def test_project_update_with_budget_and_vendor_bill(self):
        """Check project update calculations after expense budget and vendor bill.

        Verifies that budget percentages and amounts are correctly displayed in the
        project update description after creating a vendor bill.
        """
        today = date.today()
        # Use the project plan (where _column_name() returns 'account_id') so that
        # the plan column and the account_id groupby in _compute_budget are consistent,
        # and the budget report SQL JOIN matches analytic lines correctly.
        project_plan, _other_plans = self.env['account.analytic.plan']._get_all_plans()
        project_analytic_account = self.env['account.analytic.account'].create({
            'name': 'Project Budget - AA',
            'code': 'AA-BUDGET',
            'plan_id': project_plan.id,
        })
        self.project_goats.write({'account_id': project_analytic_account.id})
        plan_fname = project_analytic_account.plan_id._column_name()
        expense_account = self.env['account.account'].create({
            'name': 'Test Expense Account',
            'code': 'TESTEXP',
            'account_type': 'expense',
        })
        budget = self.env['budget.analytic'].create({
            'name': 'Project Goats Expense Budget',
            'date_from': today.replace(day=1),
            'date_to': today + relativedelta(months=1, days=-1),
            'budget_type': 'expense',
            'budget_line_ids': [Command.create({
                plan_fname: project_analytic_account.id,
                'budget_amount': 10000,
            })],
        })
        budget.action_budget_confirm()
        self.assertEqual(self.project_goats.account_id, project_analytic_account)
        self.assertEqual(self.project_goats.total_budget_amount, 10000.0)

        vendor_bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.partner_1.id,
            'invoice_date': today,
            'invoice_line_ids': [Command.create({
                'name': 'Test Expense',
                'account_id': expense_account.id,
                'price_unit': 1000.0,
                'analytic_distribution': {project_analytic_account.id: 100},
            })],
        })
        vendor_bill.action_post()
        # Invalidate cached achieved_amount so it is recomputed from budget.report
        budget.budget_line_ids.invalidate_recordset(['achieved_amount'])
        update = self.env['project.update'].with_context({'default_project_id': self.project_goats.id}).create({
            'name': 'Test',
        })
        description_body = lxml.html.fromstring(update.description)
        description_string = lxml.html.tostring(description_body.xpath('//div[@name="budget"]')[0]).decode('utf-8')
        self.assertEqual(update.project_id, self.project_goats)
        self.assertNotIn('-10.0%', description_string)
        self.assertIn('1,000.00', description_string)
        self.assertIn('10,000.00', description_string)
        self.assertIn('90.0%', description_string)
        self.assertIn('9,000.00', description_string)
        self.assertNotIn('11,000.00', description_string)
