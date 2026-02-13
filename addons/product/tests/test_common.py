# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import AccessError
from odoo.tests import tagged

from odoo.addons.product.tests.common import ProductCommon


@tagged('post_install', '-at_install')
class TestProduct(ProductCommon):

    def test_common(self):
        self._enable_pricelists()
        self.assertEqual(self.product.type, 'consu')
        self.assertEqual(self.service_product.type, 'service')

        self.assertFalse(self.pricelist.item_ids)
        self.assertEqual(
            self.env['product.pricelist'].search([]),
            self.pricelist,
        )
        self.assertEqual(
            self.env['res.partner'].search([]).property_product_pricelist,
            self.pricelist,
        )
        self.assertEqual(self.pricelist.currency_id.name, self.currency.name)

    def test_any_user_can_print_product_labels(self):
        base_user = self.env['res.users'].create({
            'name': 'Base user',
            'login': 'base_user',
            'email': 'base.user@test.com',
            'group_ids': self.group_user,
        })
        print_label_action = self.env.ref('product.action_product_template_print_labels')
        context = {
            'active_model': 'product.template',
            'active_id': self.product.product_tmpl_id,
        }
        try:
            print_label_action.with_user(base_user).with_context(context).run()
        except AccessError:
            self.fail("AccessError raised while printing product label with base user.")
