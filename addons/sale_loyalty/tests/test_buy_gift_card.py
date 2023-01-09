# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.tests.common import tagged

@tagged('-at_install', 'post_install')
class TestBuyGiftCard(TestSaleCouponCommon):

    def test_buying_gift_card(self):
        order = self.empty_order
        self.immediate_promotion_program.active = False
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_gift_card.id,
                'name': 'Gift Card Product',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.assertEqual(len(order.order_line.ids), 2)
        self.assertEqual(len(order._get_reward_coupons()), 0)
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), 1)
        order.order_line[1].product_uom_qty = 2
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), 2)
        order.order_line[1].product_uom_qty = 1
        order._update_programs_and_rewards()
        self.assertEqual(len(order._get_reward_coupons()), 1)
