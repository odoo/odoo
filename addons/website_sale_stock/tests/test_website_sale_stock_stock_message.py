# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged
from odoo.addons.sale.tests.product_configurator_common import TestProductConfiguratorCommon
from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website.tests.common import HttpCaseWithWebsiteUser

@tagged('post_install', '-at_install')
class TestWebsiteSaleStockProductConfigurator(TestProductConfiguratorCommon, HttpCaseWithUserPortal, HttpCaseWithWebsiteUser):

    def test_01_stock_message_update_after_close_with_optional_products(self):
        product_product_with_options = self.env['product.product'].create({
            'name': 'Product With Optional (TEST)',
            'standard_price': 500.0,
            'list_price': 750.0,
            'optional_product_ids': [(4, self.product_product_conf_chair.id)],
            'website_published': True,
            'show_availability': True,
            'available_threshold': 5000,
            'allow_out_of_stock_order': False,
            'is_storable': True,
        })
        self.product_product_conf_chair.website_published = True
        self.env['stock.quant'].create({
            'product_id': product_product_with_options.id,
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 30.0,
        })
        self.start_tour("/", 'website_sale_stock_message_after_close_onfigurator_modal_with_optional_products', login="website_user")

    def test_02_stock_message_update_after_close_without_optional_products(self):
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
            'location_id': self.env.ref('stock.stock_location_stock').id,
            'quantity': 30.0,
        })
        self.start_tour("/", 'website_sale_stock_message_after_close_onfigurator_modal_without_optional_products', login="website_user")
