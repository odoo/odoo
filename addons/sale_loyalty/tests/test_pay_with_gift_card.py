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

    def test_paying_with_gift_card_and_discount(self):
        # Test that discounts take precedence on payment rewards
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 50,
        }).generate_coupons()
        gift_card_1 = self.program_gift_card.coupon_ids
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_C.id,
                'name': 'Ordinary Product C',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.env['loyalty.program'].create({
            'name': 'Code for 10% on orders',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'test_10pc',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        self.assertEqual(order.amount_total, 100)
        self._apply_promo_code(order, gift_card_1.code)
        self.assertEqual(order.amount_total, 50)
        self._apply_promo_code(order, "test_10pc")
        # real flows also have to update the programs and rewards
        order._update_programs_and_rewards()
        self.assertEqual(order.amount_total, 40) # 100 - 10% - 50

    def test_paying_with_gift_card_blocking_discount(self):
        # Test that a payment program making the order total 0 still allows the user to claim discounts
        self.env['loyalty.generate.wizard'].with_context(active_id=self.program_gift_card.id).create({
            'coupon_qty': 1,
            'points_granted': 100,
        }).generate_coupons()
        gift_card_1 = self.program_gift_card.coupon_ids
        order = self.empty_order
        order.write({'order_line': [
            Command.create({
                'product_id': self.product_C.id,
                'name': 'Ordinary Product C',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.env['loyalty.program'].create({
            'name': 'Code for 10% on orders',
            'trigger': 'with_code',
            'program_type': 'promotion',
            'applies_on': 'current',
            'rule_ids': [(0, 0, {
                'mode': 'with_code',
                'code': 'test_10pc',
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'discount',
                'discount_mode': 'percent',
                'discount': 10,
                'discount_applicability': 'order',
                'required_points': 1,
            })],
        })
        self.assertEqual(order.amount_total, 100)
        self._apply_promo_code(order, gift_card_1.code)
        self.assertEqual(order.amount_total, 0)
        self._apply_promo_code(order, "test_10pc")
        # real flows also have to update the programs and rewards
        order._update_programs_and_rewards()
        self.assertEqual(order.amount_total, 0) # 100 - 10% - 90
