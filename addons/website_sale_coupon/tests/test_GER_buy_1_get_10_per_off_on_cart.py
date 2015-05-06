# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

        ######### Buy laptop and get 10% off on cart using the coupon code
        coupon = self.SaleCoupon.create({'program_id': self.couponprogram_7.id, 'nbr_uses': 1})
        #enter the code on empty cart
        applied_coupon_status = order_id.apply_coupon_reward(coupon.coupon_code)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product)
        self.assertFalse(reward_line, "Reward line is created improperly")
        self.assertTrue(applied_coupon_status.get('error'), "Returing the improper error message")
        #enter the product laptop
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_laptop.id, 'product_uom_qty': 1})]})
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_laptop)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line created improperly")
        #test with the invalid code
        applied_coupon_status = order_id.apply_coupon_reward('ODOO_INVALID')
        self.assertTrue(applied_coupon_status.get('error'), "Coupon is applied incorrectly")
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line created improperly")
        #test with valid code
        order_id.apply_coupon_reward(coupon.coupon_code)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertTrue(reward_line, "Reward line is not created")
        self.assertEqual(reward_line.price_unit, -10, "Reward per amount is incorrect")
        self.assertEqual(order_id.amount_total, 90, "Total amount is incorrect")
        #unlink applicable product
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        self.assertEqual(order_id.amount_total, 0, "Toatl amount is incorrect")
