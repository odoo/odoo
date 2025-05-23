# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale.tests.common import MockRequest
from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductTemplate(HttpCase, WebsiteSaleStockCommon):

    def test_website_sale_stock_get_additional_configurator_data(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        self.env['stock.quant'].create({
            'product_id': product.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'quantity': 10,
        })

        env = self.env(user=self.public_user)
        with MockRequest(env, website=self.website.with_env(env)):
            configurator_data = self.env['product.template']._get_additional_configurator_data(
                product_or_template=product,
                date=datetime(2000, 1, 1),
                currency=self.currency,
                pricelist=self.pricelist,
            )

        self.assertEqual(configurator_data['free_qty'], 10)

    def test_get_additional_combination_info_max_combo_quantity_with_max(self):
        product_a = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        product_b = self._create_product(is_storable=True, allow_out_of_stock_order=False)
        product_c = self._create_product(is_storable=True, allow_out_of_stock_order=True)
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
        combo_a, combo_b, combo_c = self.env['product.combo'].create([
            {'name': "Combo A", 'combo_item_ids': [Command.create({'product_id': product_a.id})]},
            {'name': "Combo B", 'combo_item_ids': [Command.create({'product_id': product_b.id})]},
            {'name': "Combo C", 'combo_item_ids': [Command.create({'product_id': product_c.id})]},
        ])
        combo_product = self._create_product(
            type='combo',
            combo_ids=[
                Command.link(combo_a.id), Command.link(combo_b.id), Command.link(combo_c.id)
            ],
        )
        self.cart.order_line = [Command.create({'product_id': product_a.id, 'product_uom_qty': 3})]

        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            combination_info = self.env['product.template'].with_context(
                website_sale_stock_get_quantity=True
            )._get_additionnal_combination_info(
                combo_product,
                quantity=3,
                uom=combo_product.uom_id,
                date=datetime(2000, 1, 1),
                website=self.website
            )

        self.assertEqual(combination_info['max_combo_quantity'], 2)

    def test_get_additional_combination_info_max_combo_quantity_without_max(self):
        product = self._create_product(is_storable=True, allow_out_of_stock_order=True)
        combo = self.env['product.combo'].create({
            'name': "Test combo", 'combo_item_ids': [Command.create({'product_id': product.id})]
        })
        combo_product = self._create_product(type='combo', combo_ids=[Command.link(combo.id)])

        with MockRequest(self.env, website=self.website, sale_order_id=self.cart.id):
            combination_info = self.env['product.template'].with_context(
                website_sale_stock_get_quantity=True
            )._get_additionnal_combination_info(
                combo_product,
                quantity=3,
                uom=combo_product.uom_id,
                date=datetime(2000, 1, 1),
                website=self.website
            )

        self.assertNotIn('max_combo_quantity', combination_info)
