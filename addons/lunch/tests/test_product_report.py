# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.lunch.tests.common import TestsCommon


class TestLunchProductReport(TestsCommon):
    def test_product_available(self):
        self.assertTrue(self.env['lunch.product.report'].search([]), 'There should be some record on lunch_product_report')

    def test_order_in_report(self):
        pizza = self.env['lunch.product.report'].search([('product_id', '=', self.product_pizza.id)], limit=1)
        self.assertEqual(pizza.name, 'Pizza')
        pizza = pizza.with_user(pizza.user_id)
        pizza.write({'is_favorite': True})
        self.assertTrue(pizza.product_id in pizza.user_id.favorite_lunch_product_ids)

        new_pizza = self.env['lunch.product.report'].search([('product_id', '=', self.product_pizza.id), ('user_id', '=', pizza.user_id.id)])

        self.assertEqual(new_pizza.id, pizza.id)
        self.assertEqual(new_pizza.name, 'Pizza')
