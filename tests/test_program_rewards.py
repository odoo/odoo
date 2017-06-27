# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.sale_coupon.tests.common import TestSaleCouponCommon

class TestSaleCouponProgramRules(TestSaleCouponCommon):
    # Test all the kind of reward a customer can receive.
    # The product reward is already tested in the basic operations test

    def test_program_rewards(self):
        # Test case: Based on the partners domain

        self.immediate_promotion_program.write({'reward_type': "discount"})

        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            }),
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should have been applied as the partner is correct, the discount is not created")


    def test_program_rewards_discount(self):

        # Test case 1: 1% discount on total order
        program = self.env['sale.coupon.program'].create({
            'name': 'Buy at least 1000 EUR, ',
            'rule_minimum_amount': 1000.0,
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'discount',
            'discount_type': 'percentage',
            'discount_percentage': 1.0,
            'discount_apply_on': 'on_order',
            'active': True,
        })
        order = self.env['sale.order'].create({
            'partner_id': self.steve.id
        })
        self.env['sale.order.line'].create({
            'product_id': self.product_A.id,
            'name': '1 Product A',
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 11.0,
            'order_id': order.id,
        })
        self.env['sale.order.line'].create({
            'product_id': self.product_B.id,
            'name': '2 Product B',
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
            'order_id': order.id,
        })
