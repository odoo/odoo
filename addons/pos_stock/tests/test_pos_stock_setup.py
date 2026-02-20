# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo
from odoo.addons.pos_stock.tests.common import TestPosStockCommon


@odoo.tests.tagged('post_install', '-at_install')
class TestPosStockSetup(TestPosStockCommon):
    def setUp(self):
        super().setUp()
        self.config = self.basic_config
        self.products = [
            self.create_product('Product 1', self.categ_basic, lst_price=10.0, standard_price=5),
            self.create_product('Product 2', self.categ_basic, lst_price=20.0, standard_price=10),
            self.create_product('Product 3', self.categ_basic, lst_price=30.0, standard_price=15),
        ]

    def test_product_categories(self):
        # check basic product category
        # it is expected to have standard and manual_periodic valuation
        self.assertEqual(self.categ_basic.property_cost_method, 'standard')
        self.assertEqual(self.categ_basic.property_valuation, 'periodic')
        # check anglo saxon product category
        # this product categ is expected to have fifo and real_time valuation
        self.assertEqual(self.categ_anglo.property_cost_method, 'fifo')
        self.assertEqual(self.categ_anglo.property_valuation, 'real_time')
