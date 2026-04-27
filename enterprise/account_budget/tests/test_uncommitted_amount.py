from odoo import Command
from .common import TestAccountBudgetCommon
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestUncommittedAmount(TestAccountBudgetCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.one_thousand_budget = cls.env['budget.analytic'].create({
            'name': '1.000$ Budget',
            'date_from': '2025-01-01',
            'date_to': '2025-12-31',
            'budget_type': 'expense',
            'state': 'draft',
            'user_id': cls.env.ref('base.user_admin').id,
            'budget_line_ids': [
                Command.create({
                    'budget_amount': 1000,
                    cls.project_column_name: cls.analytic_account_partner_a.id,
                }),
            ]
        })
        cls.one_thousand_budget.action_budget_confirm()

    def test_uncommited_amount_is_above_budget(self):
        po = self.env['purchase.order'].create({
            'partner_id': self.partner_a.id,
            'date_order': '2025-01-11',
            'order_line': [
                Command.create({
                    'product_id': self.product_a.id,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'product_qty': 1,
                    'price_unit': 200,
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'product_qty': 1,
                    'price_unit': 200,
                }),
                Command.create({
                    'product_id': self.product_a.id,
                    'analytic_distribution': {self.analytic_account_partner_a.id: 100},
                    'product_qty': 1,
                    'price_unit': 200,
                }),
            ]
        })

        self.assertFalse(po.is_above_budget, "The purchase order should not be above budget")
        self.assertFalse(po.order_line.filtered('is_above_budget'), "No purchase order line should be above budget")

        po.order_line.price_unit = 600
        self.env['purchase.order.line'].invalidate_model(['is_above_budget'])
        self.assertTrue(po.is_above_budget, "The purchase order should be exceeding budget now.")
        self.assertFalse(po.order_line.filtered('is_above_budget'), "No purchase order line should be above budget")

        po.order_line[2].price_unit = 2000
        self.env['purchase.order.line'].invalidate_model(['is_above_budget'])
        self.assertTrue(po.is_above_budget, "The purchase order should still be exceeding budget.")
        self.assertEqual(po.order_line.mapped('is_above_budget'), [False, False, True], "The first purchase order line should go above budget on its own.")
