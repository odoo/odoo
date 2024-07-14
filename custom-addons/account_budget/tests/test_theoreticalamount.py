# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .common import TestAccountBudgetCommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestTheoreticalAmount(TestAccountBudgetCommon):
    
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        
        cls.budget_post = cls.env['account.budget.post'].create({
            'name': 'Sales',
            'account_ids': [(4, cls.copy_account(cls.company_data['default_account_revenue']).id)],
        })

        cls.crossovered_budget = cls.env['crossovered.budget'].create({
            'name': 'test budget name',
            'date_from': '2018-01-01',
            'date_to': '2018-12-31',
        })

    def assertTheoricalAmountAt(self, budget_line, frozen_date, expected_amount):
        with freeze_time(frozen_date):
            self.assertRecordValues(budget_line, [{'theoritical_amount': expected_amount}])
            budget_line.invalidate_model(['theoritical_amount'])

    def test_theoritical_amount_without_paid_date(self):
        line = self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': self.crossovered_budget.id,
            'general_budget_id': self.budget_post.id,
            'date_from': '2018-01-01',
            'date_to': '2018-12-31',
            'planned_amount': -365,
        })

        self.assertTheoricalAmountAt(line, '2018-01-01', -1.0)
        self.assertTheoricalAmountAt(line, '2018-01-02', -2.0)
        self.assertTheoricalAmountAt(line, '2018-01-03', -3.0)
        self.assertTheoricalAmountAt(line, '2018-01-11', -11.0)
        self.assertTheoricalAmountAt(line, '2018-02-20', -51.0)
        self.assertTheoricalAmountAt(line, '2018-12-31', -365.0)

    def test_theoritical_amount_with_paid_date(self):
        paid_date_line = self.env['crossovered.budget.lines'].create({
            'crossovered_budget_id': self.crossovered_budget.id,
            'general_budget_id': self.budget_post.id,
            'date_from': '2018-01-01',
            'date_to': '2018-12-31',
            'planned_amount': -365,
            'paid_date':  '2018-09-09',
        })

        self.assertTheoricalAmountAt(paid_date_line, '2018-01-01', 0.0)
        self.assertTheoricalAmountAt(paid_date_line, '2018-01-02', 0.0)
        self.assertTheoricalAmountAt(paid_date_line, '2018-09-08', 0.0)
        self.assertTheoricalAmountAt(paid_date_line, '2018-09-09', 0.0)
        self.assertTheoricalAmountAt(paid_date_line, '2018-09-10', -365.0)
        self.assertTheoricalAmountAt(paid_date_line, '2018-12-31', -365.0)
