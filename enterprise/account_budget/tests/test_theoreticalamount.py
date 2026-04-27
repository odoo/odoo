# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from .common import TestAccountBudgetCommon
from odoo.tests import tagged

from freezegun import freeze_time


@tagged('post_install', '-at_install')
class TestTheoreticalAmount(TestAccountBudgetCommon):
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.budget_analytic = cls.env['budget.analytic'].create({
            'name': 'test budget name',
            'date_from': '2018-01-01',
            'date_to': '2018-12-31',
        })

    def assertTheoricalAmountAt(self, budget_line, frozen_date, expected_amount):
        with freeze_time(frozen_date):
            self.assertRecordValues(budget_line, [{'theoritical_amount': expected_amount}])
            budget_line.invalidate_model(['theoritical_amount'])

    def test_aggregates(self):
        model = self.env['budget.line']
        field_names = ['achieved_amount', 'theoritical_amount', 'theoritical_percentage']
        self.assertEqual(
            model.fields_get(field_names, ['aggregator']),
            {
                'achieved_amount': {'aggregator': 'sum'},
                'theoritical_amount': {'aggregator': 'sum'},
                'theoritical_percentage': {'aggregator': 'avg'}
            },
            f"Fields {', '.join(map(repr, field_names))} must be flagged as aggregatable.",
        )

    def test_theoritical_amount(self):
        line = self.env['budget.line'].create({
            'budget_analytic_id': self.budget_analytic.id,
            'date_from': '2018-01-01',
            'date_to': '2018-12-31',
            'budget_amount': 365,
        })

        self.assertTheoricalAmountAt(line, '2018-01-01', 1.0)
        self.assertTheoricalAmountAt(line, '2018-01-02', 2.0)
        self.assertTheoricalAmountAt(line, '2018-01-03', 3.0)
        self.assertTheoricalAmountAt(line, '2018-01-11', 11.0)
        self.assertTheoricalAmountAt(line, '2018-02-20', 51.0)
        self.assertTheoricalAmountAt(line, '2018-12-31', 365.0)
