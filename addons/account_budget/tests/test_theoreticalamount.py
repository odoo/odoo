# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from .common import TestAccountBudgetCommon
from odoo.tests import tagged
from odoo.tools.datetime import date as datelib, datetime


_logger = logging.getLogger(__name__)

# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------
@tagged('post_install', '-at_install')
class TestTheoreticalAmount(TestAccountBudgetCommon):
    def setUp(self):
        #create the budgetary position
        with patch.object(datetime, 'now', lambda tzinfo=None: datetime(1983, 10, 30, 10, 0)), \
             patch.object(datelib, 'today', lambda tzinfo=None: datelib(1983, 10, 30)):
            super(TestTheoreticalAmount, self).setUp()
            user_type_id = self.ref('account.data_account_type_revenue')
            tag_id = self.ref('account.account_tag_operating')
            account_rev = self.env['account.account'].create({
                'code': 'Y2020',
                'name': 'Budget - Test Revenue Account',
                'user_type_id': user_type_id,
                'tag_ids': [(4, tag_id)]
            })
            buget_post = self.env['account.budget.post'].create({
                'name': 'Sales',
                'account_ids': [(4, account_rev.id)],
            })
            #create the budget and budget lines
            first_january = datetime(1983, 1, 1)
            self.last_day_of_budget = first_january.end_of('year')

            crossovered_budget = self.env['crossovered.budget'].create({
                'name': 'test budget name',
                'date_from': first_january.date(),
                'date_to': self.last_day_of_budget.date(),
            })
            crossovered_budget_line_obj = self.env['crossovered.budget.lines']
            self.line = crossovered_budget_line_obj.create({
                'crossovered_budget_id': crossovered_budget.id,
                'general_budget_id': buget_post.id,
                'date_from': first_january.date(),
                'date_to': self.last_day_of_budget.date(),
                'planned_amount': -364,
            })
            self.paid_date_line = crossovered_budget_line_obj.create({
                'crossovered_budget_id': crossovered_budget.id,
                'general_budget_id': buget_post.id,
                'date_from': first_january.date(),
                'date_to': self.last_day_of_budget.date(),
                'planned_amount': -364,
                'paid_date': datelib(1983, 9, 9),
            })

    def test_theoritical_amount_without_paid_date(self):
        test_list = [
            (datetime(1983, 1, 1), 0),
            (datetime(1983, 1, 2), -1),
            (datetime(1983, 1, 3), -2),
            (datetime(1983, 1, 11), -10),
            (datetime(1983, 2, 20), -50),
            (self.last_day_of_budget, -364),
        ]
        for date, expected_amount in test_list:
            _logger.info("Checking theoritical amount for the date: " + str(date))
            with patch.object(datetime, 'now', lambda tzinfo=None: date), \
                 patch.object(datelib, 'today', lambda tzinfo=None: date.date()):
                self.assertAlmostEqual(self.line.theoritical_amount, expected_amount)
                #invalidate the cache of the budget lines to recompute the theoritical amount at next iteration
                self.line.invalidate_cache()

    def test_theoritical_amount_with_paid_date(self):
        test_list = [
            (datetime(1983, 1, 1), 0),
            (datetime(1983, 1, 2), 0),
            (datetime(1983, 9, 9), 0),
            (datetime(1983, 9, 10), -364),
            (datetime(1983, 9, 11), -364),
            (self.last_day_of_budget, -364),
        ]
        for date, expected_amount in test_list:
            _logger.info("Checking theoritical amount for the date: " + str(date))
            with patch.object(datetime, 'now', lambda tzinfo=None: date), \
                 patch.object(datelib, 'today', lambda tzinfo=None: date.date()):
                self.assertAlmostEqual(self.paid_date_line.theoritical_amount, expected_amount)
                #invalidate the cache of the budget lines to recompute the theoritical amount at next iteration
                self.paid_date_line.invalidate_cache()

    def tearDown(self):
        super(TestTheoreticalAmount, self).tearDown()
