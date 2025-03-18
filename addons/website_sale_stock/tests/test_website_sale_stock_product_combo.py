# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductCombo(HttpCase, WebsiteSaleStockCommon):

    def test_get_max_quantity_with_max(self):
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
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [
                Command.create({'product_id': product_a.id}),
                Command.create({'product_id': product_b.id}),
            ],
        })
        self.cart.order_line = [Command.create({'product_id': product_b.id, 'product_uom_qty': 3})]

        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            self.assertEqual(combo._get_max_quantity(self.website), 7)

    def test_get_max_quantity_without_max(self):
        product_a = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        product_b = self._create_product(is_storable=True, allow_out_of_stock_order=True)
        self.env['stock.quant'].create({
            'product_id': product_a.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'quantity': 5,
        })
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [
                Command.create({'product_id': product_a.id}),
                Command.create({'product_id': product_b.id}),
            ],
        })

        self.assertIsNone(combo._get_max_quantity(self.website))
