# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.addons.sale_loyalty.tests.common import TestSaleCouponCommon
from odoo.tests.common import tagged

@tagged('-at_install', 'post_install')
class TestPayWithGiftCard(TestSaleCouponCommon):

    def test_paying_with_single_gift_card_over(self):
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card = self.program_gift_card.coupon_ids[0]
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        before_gift_card_payment = order.amount_total
        self.assertNotEqual(before_gift_card_payment, 0)
        self._apply_promo_code(order, gift_card.code)
        order.action_confirm()
        self.assertEqual(before_gift_card_payment - order.amount_total, 100 - gift_card.points)

    def test_paying_with_single_gift_card_under(self):
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card = self.program_gift_card.coupon_ids[0]
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_B.id,
                'name': 'Ordinary Product b',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        before_gift_card_payment = order.amount_total
        self.assertNotEqual(before_gift_card_payment, 0)
        self._apply_promo_code(order, gift_card.code)
        order.action_confirm()
        self.assertEqual(before_gift_card_payment - order.amount_total, 100 - gift_card.points)

    def test_paying_with_multiple_gift_card(self):
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 2,
            'points_granted': 100,
        }).generate_coupons()
        gift_card_1, gift_card_2 = self.program_gift_card.coupon_ids
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_A.id,
                'name': 'Ordinary Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 20.0,
            })
        ]})
        before_gift_card_payment = order.amount_total
        self._apply_promo_code(order, gift_card_1.code)
        self._apply_promo_code(order, gift_card_2.code)
        self.assertEqual(order.amount_total, before_gift_card_payment - 200)
