# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.addons.product.tests.common import ProductCommon
from odoo.tests import Form, tagged


@tagged('post_install', '-at_install')
class TestPospricer(ProductCommon):
    def test_pricer_display_price_compute(self):
        """ Ensure the compute method sets a default value to avoid crash. """
        product_form = Form(self.env['product.product'])
        product_form.name = "Test Product"
        product = product_form.save()
        display_price = product.pricer_display_price
        self.assertIsInstance(display_price, str)
        self.assertEqual(display_price, '')

    def test_pos_pricer_sales_pricelist(self):
        """
        Test that the pricer sales pricelist is correctly applied to products
        """
        self.env['product.pricelist.item'].create({
            'pricelist_id': self.pricelist.id,
            'compute_price': 'percentage',
            'applied_on': '3_global',
            'percent_price': 10,
        })
        ProductForm = Form(self.env['product.product'])
        ProductForm.name = "Demo Product"
        ProductForm.lst_price = 100
        ProductForm.pricer_sale_pricelist_id = self.pricelist
        self.assertEqual(ProductForm.on_sale_price, 90)
        ProductForm.save()
        # After saving, on_sale_price should change if lst_price is modified
        ProductForm.lst_price = 100
        self.assertEqual(ProductForm.on_sale_price, 90)
