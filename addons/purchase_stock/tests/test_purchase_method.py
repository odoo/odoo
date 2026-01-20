# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import TransactionCase, tagged

@tagged('-at_install', 'post_install')
class TestPurchaseMethod(TransactionCase):
    def test_product_purchase_method_with_receive_as_default_purchase_method(self):
        self.env['ir.default'].set('product.template', 'bill_policy', 'transferred', company_id=True)

        product = self.env['product.product'].create({'name': 'product_test'})
        self.assertEqual(product.bill_policy, 'transferred')

        product.write({'type': 'service'})
        self.assertEqual(product.bill_policy, 'ordered')

        product.write({'type': 'consu'})
        self.assertEqual(product.bill_policy, 'transferred')

    def test_product_purchase_method_with_purchase_as_default_purchase_method(self):
        self.env['ir.default'].set('product.template', 'bill_policy', 'ordered', company_id=True)

        product = self.env['product.product'].create({'name': 'product_test'})
        self.assertEqual(product.bill_policy, 'ordered')

        product.write({'type': 'service'})
        self.assertEqual(product.bill_policy, 'ordered')

        product.write({'type': 'consu'})
        self.assertEqual(product.bill_policy, 'ordered')
