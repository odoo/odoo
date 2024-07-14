# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_subscription_stock.tests.common_sale_subscription_stock import TestSubscriptionStockCommon
from odoo.tests import users, tagged


@tagged('post_install', '-at_install')
class TestSaleSubscriptionStockRule(TestSubscriptionStockCommon):

    def setUp(self):
        super().setUp()
        if 'mrp.production' not in self.env:
            self.skipTest('`mrp` is not installed')

    @users('admin')
    def test_post_invoice_for_mto_product(self):
        warehouse = self.env.ref('stock.warehouse0')
        route_manufacture = warehouse.manufacture_pull_id.route_id.id
        route_mto = warehouse.mto_pull_id.route_id.id

        prod = self.env['product.product'].create({
            'name': 'Test',
            'type': 'product',
            'recurring_invoice': True,
            'route_ids': [Command.link(route_manufacture), Command.link(route_mto)],
        })
        sub = self.env['sale.order'].create({
            'name': 'Order',
            'is_subscription': True,
            'partner_id': self.user_portal.partner_id.id,
            'plan_id': self.plan_month.id,
            'order_line': [
                Command.create({
                    'product_id': prod.id,
                    'product_uom_qty': 1,
                    'tax_id': [Command.clear()],
                }),
            ]
        })

        sub.action_confirm()
        inv = sub._create_invoices()
        inv.action_post()
        self.assertEqual(inv.move_type, 'out_invoice')
        self.assertEqual(inv.state, 'posted')
