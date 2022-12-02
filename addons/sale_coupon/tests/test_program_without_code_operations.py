# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_coupon.tests.common import TestSaleCouponCommon


class TestProgramWithoutCodeOperations(TestSaleCouponCommon):
    # Test some basic operation (create, write, unlink) on an immediate coupon program on which we should
    # apply or remove the reward automatically, as there's no program code.

    def test_immediate_program_basic_operation(self):

        # 2 products A are needed
        self.immediate_promotion_program.write({'rule_min_quantity': 2.0})
        order = self.empty_order
        # Test case 1 (1 A): Assert that no reward is given, as the product B is missing
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "The promo offer shouldn't have been applied as the product B isn't in the order")

        # Test case 2 (1 A 1 B): Assert that no reward is given, as the product B is not present in the correct quantity
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_B.id,
                'name': '2 Product B',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The promo offer shouldn't have been applied as 2 product A aren't in the order")

        # Test case 3 (2 A 1 B): Assert that the reward is given as the product B is now in the order
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 2.0})]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 3, "The promo offert should have been applied, the discount is not created")

        # Test case 4 (1 A 1 B): Assert that the reward is removed as we don't buy 2 products B anymore
        order.write({'order_line': [(1, order.order_line[0].id, {'product_uom_qty': 1.0})]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The promo reward should have been removed as the rules are not matched anymore")
        self.assertEqual(order.order_line[0].product_id.id, self.product_A.id, "The wrong line has been removed")
        self.assertEqual(order.order_line[1].product_id.id, self.product_B.id, "The wrong line has been removed")

        # Test case 5 (1 B): Assert that the reward is removed when the order is modified and doesn't match the rules anymore
        order.write({'order_line': [
            (1, order.order_line[0].id, {'product_uom_qty': 2.0}),
            (2, order.order_line[0].id, False)
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "The promo reward should have been removed as the rules are not matched anymore")
        self.assertEqual(order.order_line.product_id.id, self.product_B.id, "The wrong line has been removed")

    def test_program_specific_product_discount(self):
        # Test if only the best promotion program is applied on a specific product
        promotion_program_specific_product_qty_2 = self.env['coupon.program'].create({
            'name': 'Buy 2 products, 10 percent discount on A',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'discount',
            'discount_type': 'percentage',
            'discount_percentage': 10,
            'rule_min_quantity': 2,
            'active': True,
            'discount_apply_on': 'specific_products',
            'discount_specific_product_ids': self.product_A,
        })

        promotion_program_specific_product_qty_5 = self.env['coupon.program'].create({
            'name': 'Buy 5 products, 20 percent discount on A',
            'promo_code_usage': 'no_code_needed',
            'reward_type': 'discount',
            'discount_type': 'percentage',
            'discount_percentage': 20,
            'rule_min_quantity': 5,
            'active': True,
            'discount_apply_on': 'specific_products',
            'discount_specific_product_ids': self.product_A,
        })

        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': 'Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 2.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The sale order has to contain two lines (the product and the promotion)")
        self.assertEqual(order._get_applied_programs(), promotion_program_specific_product_qty_2,
            "The best promotion program must be applied for a quantity equal to 2")

        order.write({'order_line': [
            (1, order.order_line.filtered(lambda l: l.name == 'Product A').id, {
                'product_uom_qty': 5.0,
            })
        ]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "The sale order has to contain two lines (the product and the promotion)")
        self.assertEqual(order._get_applied_programs(), promotion_program_specific_product_qty_5,
            "The best promotion program must be applied for a quantity equal to 5")
