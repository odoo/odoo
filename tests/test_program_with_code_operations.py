# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp.addons.sale_coupon.tests.common import TestSaleCouponCommon
from odoo.exceptions import UserError


class TestProgramWithCodeOperations(TestSaleCouponCommon):
    # Test the basic operation (apply_coupon) on an coupon program on which we should
    # apply the reward when the code is correct or remove the reward automatically when the reward is
    # not valid anymore.

    def test_program_basic_operation_coupon_code(self):
        # Test case: Generate a coupon for my customer, and add a reward then remove it automatically

        self.code_promotion_program.reward_type = 'discount'

        self.env['sale.coupon.generate'].with_context(active_id=self.code_promotion_program.id).create({
            'generation_type': 'nbr_customer',
            'partners_domain': "[('id', 'in', [%s])]" % (self.steve.id),
        }).generate_coupon()

        # Test the valid code on a wrong sales order
        wrong_partner_order = self.env['sale.order'].create({
            'partner_id': self.env.ref('base.res_partner_1').id,
        })
        with self.assertRaises(UserError):
            self.env['sale.coupon.apply.code'].with_context(active_id=wrong_partner_order.id).create({
                'coupon_code': self.code_promotion_program.coupon_ids.code
            }).process_coupon()

        # Test now on a valid sales order
        order = self.empty_order
        order.write({'order_line': [
            (0, False, {
                'product_id': self.product_A.id,
                'name': '1 Product A',
                'product_uom': self.uom_unit.id,
                'product_uom_qty': 1.0,
            })
        ]})
        self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
            'coupon_code': self.code_promotion_program.coupon_ids.code
        }).process_coupon()
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2)

        # Remove the product A from the sale order
        order.write({'order_line': [(2, order.order_line[0].id, False)]})
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 0)

def test_on_next_order_reward_promo_program(self):
    # Test case: Apply a program that generates a coupon, which is used afterward

    self.immediate_promotion_program.write({
        'promo_applicability': 'on_next_order',
        'promo_code_usage': 'code_needed',
        'promo_code': 'bleurk',
    })

    order = self.empty_order
    order.write({'order_line': [
        (0, False, {
            'product_id': self.product_A.id,
            'name': '1 Product A',
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
    ]})

    self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
        'coupon_code': 'bleurk'
    }).process_coupon()
    # Ensure that the coupon is correctly generated
    order.recompute_coupon_lines()
    self.assertEqual(len(self.immediate_promotion_program.coupon_ids.ids), 1)

    generated_coupon = self.immediate_promotion_program.coupon_ids[0]
    order = self.env['sale.order'].create({
        'partner_id': self.steve.id
    })
    order.write({'order_line': [
        (0, False, {
            'product_id': self.product_B.id,
            'name': '1 Product B',
            'product_uom': self.uom_unit.id,
            'product_uom_qty': 1.0,
        })
    ]})
    self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
        'coupon_code': generated_coupon.code
    })
    # Ensure that the generated coupon is valid
    order.recompute_coupon_lines()
    self.assertEqual(len(order.order_line.ids), 2)
