# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductConfigurator(HttpCase):

    def test_website_sale_stock_product_configurator(self):
        optional_product = self.env['product.template'].create({
            'name': "Optional product",
            'website_published': True,
        })
        main_product = self.env['product.product'].create({
            'name': "Main product",
            'website_published': True,
            'is_storable': True,
            'allow_out_of_stock_order': False,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        self.env['stock.quant'].create({
            'product_id': main_product.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 10,
        })
        self.start_tour('/', 'website_sale_stock_product_configurator', login='admin')

    def test_website_sale_stock_product_configurator_out_of_stock(self):
        """ Test that out of stock options can't be sold. """
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
        self.env['product.product'].create({
            'name': "Main product",
            'website_published': True,
            'optional_product_ids': [Command.set(optional_product.ids)],
        })
        self.env['stock.quant'].create({
            'product_id': optional_product.product_variant_ids[1].id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 10,
        })
        self.start_tour('/', 'website_sale_stock_product_configurator_out_of_stock', login='admin')
