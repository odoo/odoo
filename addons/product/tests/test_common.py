# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestProductCommon(ProductCommon):

    def test_common(self):
        self.assertEqual(self.consumable_product.type, 'consu')
        self.assertEqual(self.service_product.type, 'service')

        account_module = self.env['ir.module.module']._get('account')
        if account_module.state == 'installed':
            self.assertFalse(self.consumable_product.taxes_id)
            self.assertFalse(self.service_product.taxes_id)

        self.assertFalse(self.pricelist.item_ids)
        self.assertEqual(
            self.env['product.pricelist'].search([]),
            self.pricelist,
        )
        self.assertEqual(
            self.env['res.partner'].search([]).property_product_pricelist,
            self.pricelist,
        )
        self.assertEqual(self.pricelist.currency_id.name, 'USD')
        self.assertEqual(self.pricelist.discount_policy, 'with_discount')
