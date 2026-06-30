# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase

from odoo.addons.website_sale.tests.common import MockRequest
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
            self.assertEqual(combo._get_max_quantity(self.website, self.cart), 7)

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

        self.assertIsNone(combo._get_max_quantity(self.website, self.cart))

    def test_website_sale_stock_max_combo(self):
        """
        Ensure we cannot add to the cart more units of a combo product than what is available in
        stock (the maximum quantity of its combo items).
        """
        product1 = self._create_product(name='Test product1')
        self.env['stock.quant']._update_available_quantity(product1, self.warehouse.lot_stock_id, 2)
        product2 = self._create_product(name='Test product2')
        self.env['stock.quant']._update_available_quantity(product2, self.warehouse.lot_stock_id, 1)
        self._create_product(
            name='ComboProduct',
            type='combo',
            combo_ids=[Command.create({
                'name': 'Test combo',
                'combo_item_ids': [
                    Command.create({'product_id': product1.id}),
                    Command.create({'product_id': product2.id}),
                ],
            })],
        )
        self.start_tour('/shop?search=ComboProduct', 'test_website_sale_stock_max_combo')
