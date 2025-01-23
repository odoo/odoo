# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged

@tagged('-at_install', 'post_install')
class TestPurchaseMethod(TransactionCase):
    def test_product_purchase_method(self):
        """
        Test the default purchase method based on product type:
            - For 'consu' (Goods) product type, the default purchase method is 'receive'.
            - For 'service' product type, the default purchase method is 'purchase'.
        The test ensures that when the product type is changed, the corresponding purchase method is set correctly.
        """
        product = self.env['product.product'].create({'name': 'product_test'})
        self.assertEqual(product.purchase_method, 'receive')

        product.write({'type': 'service'})
        self.assertEqual(product.purchase_method, 'purchase')

        product.write({'type': 'consu'})
        self.assertEqual(product.purchase_method, 'receive')
