# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {'product_id': self.product_mobile.id, 'product_uom_qty': 1})]})

        # ########### purchase for 1500 and above and get 10% off on cart
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_cover.id, 'product_uom_qty': 30})]})
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_cover)
        #product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_cover)
        self.assertEqual(order_id.amount_total, 1350, "Total amount is invalid")
        self.assertTrue(reward_line, "Reward is not created")
        self.assertEqual(reward_line.price_unit, -150, "Reward on amount percentage is incorrect")
        # #update the qty of product so that cart amount is less than 1500
        applicable_line.write({'product_uom_qty': 5})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        self.assertFalse(reward_line, "Reward is not deleting properly")
        self.assertEqual(order_id.amount_total, 250, "Total amount is invalid")
        #update the qty of applicable product
        applicable_line.write({'product_uom_qty': 30})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        self.assertTrue(reward_line, "Reward line is not created properly")
        self.assertEqual(order_id.amount_total, 1350, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -150, "Reward on amount percentage is incorrect")
        #unlink the applicable product line
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is False)
        self.assertFalse(reward_line, "Reward line is created improperly")
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")
