# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.tests.account_test_classes import AccountingTestCase

import time


class TestAccountBudgetCommon(AccountingTestCase):

    def setUp(self):
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
            'date_from': str(time.localtime(time.time())[0] + 1) + '-01-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-01-31',
            'planned_amount': 500.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-02-07',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-02-28',
            'planned_amount': 900.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-03-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-03-15',
            'planned_amount': 300.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_our_super_product'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-03-16',
            'paid_date': str(time.localtime(time.time())[0] + 1) + '-12-03',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-03-31',
            'planned_amount': 375.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_our_super_product'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-05-01',
            'paid_date': str(time.localtime(time.time())[0] + 1) + '-12-03',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-05-31',
            'planned_amount': 375.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-07-16',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-07-31',
            'planned_amount': 20000.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-02-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-02-28',
            'planned_amount': 20000.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-09-16',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-09-30',
            'planned_amount': 10000.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_sales0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-10-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-12-31',
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
            'date_from': str(time.localtime(time.time())[0] + 1) + '-01-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-01-31',
            'planned_amount': -500.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-02-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-02-28',
            'planned_amount': -250.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_our_super_product'),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-04-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-04-30',
            'planned_amount': -150.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-06-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-06-15',
            'planned_amount': -7500.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-06-16',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-06-30',
            'planned_amount': -5000.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-07-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-07-15',
            'planned_amount': -2000.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-08-16',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-08-31',
            'planned_amount': -3000.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetpessimistic0'),
        })
        self.env['crossovered.budget.lines'].create({
            'analytic_account_id': self.ref('analytic.analytic_seagate_p2'),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'date_from': str(time.localtime(time.time())[0] + 1) + '-09-01',
            'date_to': str(time.localtime(time.time())[0] + 1) + '-09-15',
            'planned_amount': -1000.0,
            'crossovered_budget_id': self.ref('account_budget.crossovered_budget_budgetoptimistic0'),
        })
