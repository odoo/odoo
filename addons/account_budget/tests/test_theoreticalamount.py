# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from .common import TestAccountBudgetCommon
try:
    from unittest.mock import patch
except ImportError:
    from mock import patch

from odoo.fields import Datetime

# ---------------------------------------------------------
# Tests
# ---------------------------------------------------------
class TestTheoreticalAmount(TestAccountBudgetCommon):
    def setUp(self):
        super(TestTheoreticalAmount, self).setUp()
        crossovered_budget = self.env['crossovered.budget'].create({
            'name': 'test budget name',
            'date_from': '2014-01-01',
            'date_to': '2014-12-31',
        })
        crossovered_budget_line_obj = self.env['crossovered.budget.lines']
        user_type_id = self.ref('account.data_account_type_revenue')
        tag_id = self.ref('account.account_tag_operating')
        account_rev = self.env['account.account'].create({
            'code': 'Y2020',
            'name': 'Budget - Test Revenue Account',
            'user_type_id': user_type_id,
            'tag_ids': [(4, tag_id, 0)]
        })
        buget_post = self.env['account.budget.post'].create({
            'name': 'Sales',
            'account_ids': [(4, account_rev.id, 0)],
        })
        self.line = crossovered_budget_line_obj.create({
            'crossovered_budget_id': crossovered_budget.id,
            'general_budget_id': buget_post.id,
            'date_from': '2014-01-01',
            'date_to': '2014-12-31',
            'planned_amount': -364,
        })

        self.patcher = patch('odoo.addons.account_budget.models.account_budget.fields.Datetime', wraps=Datetime)
        self.mock_datetime = self.patcher.start()

    def test_01(self):
        """Start"""
        date = Datetime.to_string(Datetime.from_string('2014-01-01 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, 0)

    def test_02(self):
        """After 24 hours"""
        date = Datetime.to_string(Datetime.from_string('2014-01-02 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -1)

    def test_03(self):
        """After 36 hours"""
        date = Datetime.to_string(Datetime.from_string('2014-01-02 12:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -1.5)

    def test_04(self):
        """After 48 hours"""
        date = Datetime.to_string(Datetime.from_string('2014-01-03 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -2)

    def test_05(self):
        """After 10 days"""
        date = Datetime.to_string(Datetime.from_string('2014-01-11 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -10)

    def test_06(self):
        """After 50 days"""
        date = Datetime.to_string(Datetime.from_string('2014-02-20 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -50)

    def test_07(self):
        """After 182 days, exactly half of the budget line"""
        date = Datetime.to_string(Datetime.from_string('2014-07-02 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -182)

    def test_08(self):
        """After 308 days at noon"""
        date = Datetime.to_string(Datetime.from_string('2014-11-05 12:00:00'))  # remember, remember
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -308.5)

    def test_09(self):
        """One day before"""
        date = Datetime.to_string(Datetime.from_string('2014-12-30 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -363)

    def test_10(self):
        """At last"""
        date = Datetime.to_string(Datetime.from_string('2014-12-31 00:00:00'))
        self.mock_datetime.now.return_value = date
        self.assertAlmostEqual(self.line.theoritical_amount, -364)

    def tearDown(self):
        self.patcher.stop()
        super(TestTheoreticalAmount, self).tearDown()
