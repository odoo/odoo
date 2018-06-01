# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from unittest.mock import patch

from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.tools.datetime import date as datelib, datetime

class TestAccountBudgetCommon(AccountingTestCase):

    def setUp(self):
        with patch.object(datetime, 'now', lambda tzinfo=None: datetime(1983, 10, 30, 10, 0)), \
             patch.object(datelib, 'today', lambda tzinfo=None: datelib(1983, 10, 30)):
            super(TestAccountBudgetCommon, self).setUp()
            # In order to check account budget module in Odoo I created a budget with few budget positions
            # Checking if the budgetary positions have accounts or not
            account_ids = self.env['account.account'].search([
                ('user_type_id', '=', self.ref('account.data_account_type_revenue')),
                ('tag_ids.name', 'in', ['Operating Activities'])
            ]).ids
            if not account_ids:
                account_ids = self.env['account.account'].create({
                    'name': 'Product Sales - (test)',
                    'code': 'X2020',
                    'user_type_id': self.ref('account.data_account_type_revenue'),
                    'tag_ids': [(6, 0, [self.ref('account.account_tag_operating')])],
                }).ids
            self.account_budget_post_sales0 = self.env['account.budget.post'].create({
                'name': 'Sales',
                'account_ids': [(6, None, account_ids)],
            })

            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 1, 1),
                'date_to': datetime(1983, 1, 31),
                'planned_amount': 500.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 2, 7),
                'date_to': datetime(1983, 2, 28),
                'planned_amount': 900.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 3, 1),
                'date_to': datetime(1983, 3, 15),
                'planned_amount': 300.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_our_super_product'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 3, 16),
                'paid_date': datetime(1983, 12, 3),
                'date_to': datetime(1983, 3, 31),
                'planned_amount': 375.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_our_super_product'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 5, 1),
                'paid_date': datetime(1983, 12, 3),
                'date_to': datetime(1983, 5, 31),
                'planned_amount': 375.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 7, 16),
                'date_to': datetime(1983, 7, 31),
                'planned_amount': 20000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 2, 1),
                'date_to': datetime(1983, 2, 28),
                'planned_amount': 20000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 9, 16),
                'date_to': datetime(1983, 9, 30),
                'planned_amount': 10000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_sales0.id,
                'date_from': datetime(1983, 10, 1),
                'date_to': datetime(1983, 12, 31),
                'planned_amount': 10000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })

            account_ids = self.env['account.account'].search([
                ('user_type_id.name', '=', 'Expenses'),
                ('tag_ids.name', 'in', ['Operating Activities'])
            ]).ids

            if not account_ids:
                account_ids = self.env['account.account'].create({
                    'name': 'Expense - (test)',
                    'code': 'X2120',
                    'user_type_id': self.ref('account.data_account_type_expenses'),
                    'tag_ids': [(6, 0, [self.ref('account.account_tag_operating')])],
                }).ids
            self.account_budget_post_purchase0 = self.env['account.budget.post'].create({
                'name': 'Purchases',
                'account_ids': [(6, None, account_ids)],
            })

            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 1, 1),
                'date_to': datetime(1983, 1, 31),
                'planned_amount': -500.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 2, 1),
                'date_to': datetime(1983, 2, 28),
                'planned_amount': -250.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_our_super_product'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 4, 1),
                'date_to': datetime(1983, 4, 30),
                'planned_amount': -150.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 6, 1),
                'date_to': datetime(1983, 6, 15),
                'planned_amount': -7500.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 6, 16),
                'date_to': datetime(1983, 6, 30),
                'planned_amount': -5000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 7, 1),
                'date_to': datetime(1983, 7, 15),
                'planned_amount': -2000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 8, 16),
                'date_to': datetime(1983, 8, 31),
                'planned_amount': -3000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
            })
            self.env['crossovered.budget.lines'].create({
                'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
                'general_budget_id': self.account_budget_post_purchase0.id,
                'date_from': datetime(1983, 9, 1),
                'date_to': datetime(1983, 9, 15),
                'planned_amount': -1000.0,
                'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
            })
