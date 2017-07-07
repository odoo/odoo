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
        self.assertEqual(len(order.order_line.ids), 4)

        # Test case 3: the amount is not sufficient now, the reward should be removed
        order.write({'order_line': [
            (2, order.order_line.filtered(lambda line: line.product_id.id == self.product_A.id).id, False)
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2)
