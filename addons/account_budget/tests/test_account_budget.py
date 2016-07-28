# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
from odoo.fields import Date

import datetime

# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------
class TestAccountBudget(TestAccountBudgetCommon):

    def test_account_budget(self):
        # In order to check account budget module in Odoo I created a budget with few budget positions
        # Checking if the budgetary positions have accounts or not
        if not self.account_budget_post_sales0.account_ids:
            a_sale = self.env['account.account'].create({
                'name': 'Product Sales - (test)',
                'code': 'X2020',
                'user_type_id': self.ref('account.data_account_type_revenue'),
                'tag_ids': [(6, 0, [self.ref('account.account_tag_operating')])],
            })
            self.account_budget_post_sales0.write({'account_ids': [(6, 0, [a_sale.id])]})
        if not self.account_budget_post_purchase0.account_ids:
            a_expense = self.env['account.account'].create({
                'name': 'Expense - (test)',
                'code': 'X2120',
                'user_type_id': self.ref('account.data_account_type_expenses'),
                'tag_ids': [(6, 0, [self.ref('account.account_tag_operating')])],
            })
            self.account_budget_post_purchase0.write({'account_ids': [(6, 0, [a_expense.id])]})

        # Creating a crossovered.budget record
        budget = self.env['crossovered.budget'].create({
            'date_from': Date.from_string('%s-01-01' % (datetime.datetime.now().year + 1)),
            'date_to': Date.from_string('%s-12-31' % (datetime.datetime.now().year + 1)),
            'name': 'Budget %s' % (datetime.datetime.now().year + 1),
            'state': 'draft'
        })

        # I created two different budget lines
        # Modifying a crossovered.budget record
        self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': budget.id,
            'analytic_account_id': self.ref('analytic.analytic_partners_camp_to_camp'),
            'date_from': Date.from_string('%s-01-01' % (datetime.datetime.now().year + 1)),
            'date_to': Date.from_string('%s-12-31' % (datetime.datetime.now().year + 1)),
            'general_budget_id': self.account_budget_post_purchase0.id,
            'planned_amount': 10000.0,
        })
        self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': budget.id,
            'analytic_account_id': self.ref('analytic.analytic_our_super_product'),
            'date_from': Date.from_string('%s-09-01' % (datetime.datetime.now().year + 1)),
            'date_to': Date.from_string('%s-09-30' % (datetime.datetime.now().year + 1)),
            'general_budget_id': self.account_budget_post_sales0.id,
            'planned_amount': 400000.0,
        })
        # I check that Initially Budget is in "draft" state
        self.assertEqual(budget.state, 'draft')

        # I pressed the confirm button to confirm the Budget
        # Performing a workflow action confirm on module crossovered.budget
        budget.signal_workflow('confirm')

        # I check that budget is in "Confirmed" state
        self.assertEqual(budget.state, 'confirm')

        # I pressed the validate button to validate the Budget
        # Performing a workflow action validate on module crossovered.budget
        budget.signal_workflow('validate')

        # I check that budget is in "Validated" state
        self.assertEqual(budget.state, 'validate')

        # I pressed the done button to set the Budget to "Done" state
        # Performing a workflow action done on module crossovered.budget
        budget.signal_workflow('done')

        # I check that budget is in "done" state
        self.assertEqual(budget.state, 'done')
