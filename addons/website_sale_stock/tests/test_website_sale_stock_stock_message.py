# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductConfigurator(ProductCommon, HttpCase):

    def test_01_stock_message_update_after_close_with_optional_products(self):
        self.env['delivery.carrier'].search([]).is_published = False
        product_product_with_options = self.env['product.product'].create({
            'name': 'Product With Optional (TEST)',
            'standard_price': 500.0,
            'list_price': 750.0,
            'optional_product_ids': [Command.link(self.product.product_tmpl_id.id)],
            'website_published': True,
            'show_availability': True,
            'available_threshold': 5000,
            'allow_out_of_stock_order': False,
            'is_storable': True,
        })
        self.product.website_published = True
        self.env['stock.quant'].create({
            'product_id': product_product_with_options.id,
            'location_id': self.quick_ref('stock.stock_location_stock').id,
            'quantity': 30.0,
        })
        self.start_tour(
            "/",
            'website_sale_stock_message_after_close_onfigurator_modal_with_optional_products',
        )

    def test_02_stock_message_update_after_close_without_optional_products(self):
        self.env['delivery.carrier'].search([]).is_published = False
        product_product_without_options = self.env['product.product'].create({
            'name': 'Product Without Optional (TEST)',
            'standard_price': 500.0,
            'list_price': 750.0,
            'website_published': True,
            'show_availability': True,
            'available_threshold': 5000,
            'allow_out_of_stock_order': False,
            'is_storable': True,
        })
        self.env['stock.quant'].create({
            'product_id': product_product_without_options.id,
            'location_id': self.quick_ref('stock.stock_location_stock').id,
            'quantity': 30.0,
        })
        self.start_tour(
            "/",
            'website_sale_stock_message_after_close_onfigurator_modal_without_optional_products',
        )
