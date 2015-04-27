# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

        ######### Public unique code - Buy 1 shoe + get 1 socks free
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_shoe.id, 'product_uom_qty': 1})]})
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_shoe)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line is created before entering the code")
        #test with invalid code
        applied_coupon_status = order_id.apply_coupon_reward('ODOO_INVALID')
        self.assertTrue(applied_coupon_status.get('error'), "Coupon is applied incorrectly")
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line is created improperly")
        #test with valid code
        order_id.apply_coupon_reward('ODOO_AAAA')
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_socks)
        self.assertTrue(reward_line, "Reward line is not created")
        self.assertTrue(product_line, "Reward product line is not created properly")
        self.assertEqual(order_id.amount_total, 100, "Total amount is incorrect")
        #re-enter the valid code
        applied_coupon_status = order_id.apply_coupon_reward('ODOO_AAAA')
        self.assertTrue(applied_coupon_status.get('error'), "Coupon is applied incorrectly")
        #unlink the reward product
        product_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        #re-enter the valid code
        order_id.apply_coupon_reward('ODOO_AAAA')
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        self.assertEqual(order_id.amount_total, 10, "Total amount is incorrect")
