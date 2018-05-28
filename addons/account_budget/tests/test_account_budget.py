# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
from odoo.fields import Date
from odoo.tests import tagged

import datetime

# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------
@tagged('post_install', '-at_install')
class TestAccountBudget(TestAccountBudgetCommon):

    def test_account_budget(self):

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
        # Performing an action confirm on module crossovered.budget
        budget.action_budget_confirm()

        # I check that budget is in "Confirmed" state
        self.assertEqual(budget.state, 'confirm')

        # I pressed the validate button to validate the Budget
        # Performing an action validate on module crossovered.budget
        budget.action_budget_validate()

        # I check that budget is in "Validated" state
        self.assertEqual(budget.state, 'validate')

        # I pressed the done button to set the Budget to "Done" state
        # Performing an action done on module crossovered.budget
        budget.action_budget_done()

        # I check that budget is in "done" state
        self.assertEqual(budget.state, 'done')
