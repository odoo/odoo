# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.product.tests.common import ProductCommon
from odoo.tests import Form


class TestProductPricelistItem(ProductCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.pricelist_item = cls.env['product.pricelist.item'].create({
             'pricelist_id': cls.pricelist.id,
             'applied_on': '0_product_variant',
             'product_tmpl_id': cls.product.product_tmpl_id.id,
             'product_id': cls.product.id,
             'compute_price': 'fixed',
             'fixed_price': 50,
             'base': 'list_price',
        })

    def test_remove_product_on_0_product_variant_applied_on_rule(self):
        """Test generation of applied on based on rule data"""
        self.assertEqual(self.pricelist_item.applied_on, '0_product_variant')
        with Form(self.pricelist_item) as form:
            form.product_tmpl_id = self.env['product.template']
        #  Test values after on change
        self.assertFalse(self.pricelist_item.product_tmpl_id)
        self.assertFalse(self.pricelist_item.product_id)
        self.assertEqual(self.pricelist_item.applied_on, '3_global')
