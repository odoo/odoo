# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_sale_stock.tests.common import WebsiteSaleStockCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockConfigurators(HttpCase, WebsiteSaleStockCommon):

    def test_website_sale_stock_product_configurator(self):
        stock_attribute = self.env['product.attribute'].create({
            'name': "Stock",
            'value_ids': [
                Command.create({'name': "Out of stock"}),
                Command.create({'name': "In stock"}),
            ]
        })
        optional_product = self.env['product.template'].create({
            'name': "Optional product",
            'website_published': True,
            'is_storable': True,
            'allow_out_of_stock_order': False,
            'attribute_line_ids': [
                Command.create({
                    'attribute_id': stock_attribute.id,
                    'value_ids': [Command.set(stock_attribute.value_ids.ids)],
                })
            ],
        })
        main_product = self.env['product.product'].create({
            'name': "Main product",
            'website_published': True,
            'is_storable': True,
            'allow_out_of_stock_order': False,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        self.env['stock.quant'].create([
            {
                'product_id': optional_product.product_variant_ids[1].id,
                'location_id': self.warehouse.lot_stock_id.id,
                'quantity': 10,
            }, {
                'product_id': main_product.id,
                'location_id': self.warehouse.lot_stock_id.id,
                'quantity': 10,
            },
        ])
        self.start_tour('/', 'website_sale_stock_product_configurator')

    def test_website_sale_stock_combo_configurator(self):
        product = self._create_product(
            name="Test product",
            is_storable=True,
            allow_out_of_stock_order=False,
        )
        self.env['stock.quant'].create({
            'product_id': product.id,
            'location_id': self.warehouse.lot_stock_id.id,
            'quantity': 2,
        })
        combo = self.env['product.combo'].create({
            'name': "Test combo",
            'combo_item_ids': [
                Command.create({'product_id': product.id}),
                Command.create({'product_id': self._create_product().id}),
            ],
        })
        self._create_product(
            name="Combo product",
            type='combo',
            combo_ids=[Command.link(combo.id)]
        )
        self.start_tour('/', 'website_sale_stock_combo_configurator')
