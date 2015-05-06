# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

        # # ######### buy 2 Hard disk get 1 hard disk free
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_harddisk.id, 'product_uom_qty': 2})]})
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_harddisk)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertTrue(product_line, "Product line is not created")
        self.assertEqual(product_line.product_uom_qty, 3, "Reward product qty is invalid")
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 100, "Total amount is invalid")
        #to check unit price of reward and reward product
        self.assertEqual(product_line.price_unit, (-1) * reward_line.price_unit, "Reward unit price is incorrect")
        # #update the product qty, addition
        product_line.write({'product_uom_qty': 10})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 3, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 350, "Total amount is invalid")
        # #update the product qty, deduction
        product_line.write({'product_uom_qty': 6})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 2, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 200, "Total amount is invalid")
        # update the product qty = 1
        product_line.write({'product_uom_qty': 1})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertFalse(reward_line, "Reward line is not deleting properly")
        self.assertEqual(order_id.amount_total, 50, "Total amount is invalid")
        #update the product qty, addition
        product_line.write({'product_uom_qty': 3})
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertEqual(reward_line.product_uom_qty, 1, "Reward product qty is invalid")
        self.assertEqual(order_id.amount_total, 100, "Total amount is invalid")
        #unlink the product line, reward line should be deleted
        product_line.unlink()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertFalse(reward_line, "Reward is not deleting properly")
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")
