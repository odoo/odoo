# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

         # ##########buy 1 pen drive and get 10% off on pen drive cover
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pendrive.id, 'product_uom_qty': 1})]})
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pendrive)
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pendrive_cover)
        self.assertFalse(product_line, "Reward is created in case of reward on specific product")
        self.assertEqual(order_id.amount_total, 60, "Total amount is invalid")
        #add the reward product line
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pendrive_cover.id})]})
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pendrive_cover)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertTrue(reward_line, "reward line is not created")
        #check for reward amount and qty
        self.assertEqual(order_id.amount_total, 78, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -2, "Reward percentage is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward qty is incorrect")
        #update the applicable product qty, addition
        applicable_line.write({'product_uom_qty': 2})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 138, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -2, "Reward percentage is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward qty is incorrect")
        #add the reward product pendrive cover
        product_line.write({'product_uom_qty': 2})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 158, "Total amount is invalid")
        self.assertEqual(reward_line.price_unit, -2, "Reward percentage is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward qty is incorrect")
        # #unlink the applicable line
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 40, "Total amount is invalid")
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        product_line.unlink()
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")
