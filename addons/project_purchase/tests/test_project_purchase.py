# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command

from odoo.addons.project_purchase.tests.test_project_profitability import TestProjectPurchaseProfitability


class TestProjectPurchase(TestProjectPurchaseProfitability):

    def test_compute_purchase_orders_count(self):
        project1 = self.env['project.project'].create({'name': 'Project'})
        project1.account_id = self.analytic_account  # Project with analytics
        order_line_values = {
            'product_id': self.product_order.id,
            'product_qty': 1,
            'price_unit': self.product_order.standard_price,
            'currency_id': self.env.company.currency_id.id,
        }
        self.env['purchase.order'].create([
            {
                'name': 'Purchase Order 1',
                'partner_id': self.partner_a.id,
                'order_line': [Command.create({**order_line_values, 'analytic_distribution': {self.analytic_account.id: 100}})]
            },
            {
                'name': 'Purchase Order 2',
                'partner_id': self.partner_a.id,
                'project_id': project1.id,
                'order_line': [Command.create(order_line_values)],
            },
            {
                'name': 'Purchase Order 3',
                'partner_id': self.partner_a.id,
                'project_id': project1.id,
                'order_line': [Command.create({**order_line_values, 'analytic_distribution': {self.analytic_account.id: 100}})]
            },
        ])
        self.assertEqual(project1.purchase_orders_count, 3, 'The number of purchase orders linked to project1 should be equal to 3.')

        project2 = self.env['project.project'].create({'name': 'Project'})
        project2.account_id = False  # Project without analytics
        self.env['purchase.order'].create([
            {
                'name': 'Purchase Order 4',
                'partner_id': self.partner_a.id,
                'project_id': project2.id,
                'order_line': [Command.create(order_line_values)],
            },
            {
                'name': 'Purchase Order 5',
                'partner_id': self.partner_a.id,
                'project_id': project2.id,
                'order_line': [Command.create(order_line_values)],
            },
        ])
        self.assertEqual(project2.purchase_orders_count, 2, 'The number of purchase orders linked to project2 should be equal to 2.')
