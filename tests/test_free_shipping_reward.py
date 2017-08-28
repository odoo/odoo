# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCouponProgramRules(TestSaleCouponCommon):
    # Test a free shipping reward + some expected behavior
    # (automatic line addition or removal)

    def test_free_shipping_reward(self):
        # Test case 1: The minimum amount is not reached, the reward should
        # not be created
        self.immediate_promotion_program.active = False
        self.env['sale.coupon.program'].create({
            'name': 'Free Shipping if at least 100 euros',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'free_shipping',
            'rule_minimum_amount': 100.0,
            'active': True,
        })

        order = self.env['sale.order'].create({
            'partner_id': self.steve.id,
        })

        # Price of order will be 5*1.15 = 5.75 (tax included)
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_B.id,
                'name': 'Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1)

        order.carrier_id = self.env['delivery.carrier'].search([])[1]
        order.get_delivery_price()
        order.set_delivery_line()

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2)

        # Test Case 1b: amount is not reached but is on a threshold
        # The amount of deliverable product + the one of the delivery exceeds the minimum amount
        # yet the program shouldn't be applied

        # Order price will be 5.75 + 81.74*1.15 = 99.75
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_B.id,
                'name': 'Product 1B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
                'price_unit': 81.74,
            })
        ]})

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3)

        # Test case 2: the amount is sufficient, the shipping should
        # be reimbursed
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': 'Product 1',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
                'price_unit': 1000
            })
        ]})

        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 5)

        # Test case 3: the amount is not sufficient now, the reward should be removed
        order.write({'order_line': [
            (2, order.order_line.filtered(lambda line: line.product_id.id == self.product_A.id).id, False)
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3)
