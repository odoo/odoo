# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockSaleOrderLine(HttpCase, WebsiteSaleStockCommon):

    def test_get_max_line_qty_with_max(self):
        product_a = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        product_b = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        self.env['stock.quant'].create([
            {
                'product_id': product_a.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'quantity': 5,
            }, {
                'product_id': product_b.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'quantity': 10,
            },
        ])
        combo_a, combo_b = self.env['product.combo'].create([
            {'name': "Combo A", 'combo_item_ids': [Command.create({'product_id': product_a.id})]},
            {'name': "Combo B", 'combo_item_ids': [Command.create({'product_id': product_b.id})]},
        ])
        combo_product = self._create_product(
            type='combo', combo_ids=[Command.link(combo_a.id), Command.link(combo_b.id)]
        )
        combo_product_line = self.env['sale.order.line'].create({
            'order_id': self.cart.id, 'product_id': combo_product.id, 'product_uom_qty': 3
        })
        combo_item_line_a, _combo_item_line_b = self.env['sale.order.line'].create([
            {
                'order_id': self.cart.id,
                'product_id': product_a.id,
                'product_uom_qty': 3,
                'linked_line_id': combo_product_line.id,
                'combo_item_id': combo_a.combo_item_ids[0].id,
            }, {
                'order_id': self.cart.id,
                'product_id': product_b.id,
                'product_uom_qty': 3,
                'linked_line_id': combo_product_line.id,
                'combo_item_id': combo_b.combo_item_ids[0].id,
            },
        ])

        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            self.assertEqual(combo_product_line._get_max_available_qty(), 2)
            self.assertEqual(combo_product_line._get_max_line_qty(), 5)
            self.assertEqual(combo_item_line_a._get_max_available_qty(), 2)
            self.assertEqual(combo_item_line_a._get_max_line_qty(), 5)

    def test_get_max_line_qty_without_max(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=True)
        combo = self.env['product.combo'].create({
            'name': "Test combo", 'combo_item_ids': [Command.create({'product_id': product.id})]
        })
        combo_product = self._create_product(type='combo', combo_ids=[Command.link(combo.id)])
        combo_product_line = self.env['sale.order.line'].create({
            'order_id': self.cart.id, 'product_id': combo_product.id, 'product_uom_qty': 3,
        })
        combo_item_line = self.env['sale.order.line'].create({
            'order_id': self.cart.id,
            'product_id': product.id,
            'product_uom_qty': 3,
            'linked_line_id': combo_product_line.id,
        })

        self.assertIsNone(combo_product_line._get_max_available_qty())
        self.assertIsNone(combo_product_line._get_max_line_qty())
        self.assertIsNone(combo_item_line._get_max_available_qty())
        self.assertIsNone(combo_item_line._get_max_line_qty())
