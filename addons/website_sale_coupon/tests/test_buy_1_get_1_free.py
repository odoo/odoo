# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'order_line': [(0, 0, {'product_id': self.product_mobile.id, 'product_uom_qty': 1})]})

        ######## buy 1 mobile get 1 cover
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_cover)
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_mobile)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertEqual(order_id.amount_total, 100.00, "Toatal amount is incorrect")
        self.assertTrue(product_line, "Product line is not created")
        self.assertEqual(product_line.product_uom_qty, 1, "Reward product is not created properly")
        self.assertTrue(reward_line, "Reward line is not created")
        #to check unit price of reward and reward product
        self.assertEqual(product_line.price_unit, (-1) * reward_line.price_unit, "Reward unit price is incorrect")
        #update the mobile qty and check qty of reward,qty addition
        applicable_line.write({'product_uom_qty': 5})
        order_id.apply_immediately_reward()
        self.assertEqual(order_id.amount_total, 500.00, "Total amount is incorrect")
        self.assertEqual(reward_line.product_uom_qty, 5, "Reward qty is incorrect in addition")
        #update the mobile qty n check qty of reward,qty deduction
        applicable_line.write({'product_uom_qty': 2})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 2, "Reward qty is incorrect in deletion")
        self.assertEqual(order_id.amount_total, 350.00, "Total amount is incorrect")
        #update the qty of cover n check qty of reward, greater than reward qty
        product_line.write({'product_uom_qty': 5})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.product_uom_qty, 2, "Reward qty is incorrect")
        self.assertEqual(order_id.amount_total, 350.00, "Total amount is incorrect")
        #update the qty of cover n check qty of reward, less than reward qty
        product_line.write({'product_uom_qty': 1})
        order_id.apply_immediately_reward()
        self.assertEqual(product_line.product_uom_qty, 2, "Reward product qty is not updated")
        self.assertEqual(order_id.amount_total, 200.00, "Total amount is incorrect")
        #unlink the cover and check weather that is added automaticaly or not
        product_line.unlink()
        order_id.apply_immediately_reward()
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_cover)
        self.assertTrue(product_line, "reward product line is deleted")
        self.assertEqual(order_id.amount_total, 200.00, "Total amount is incorrect")
        #unlink the mobile line and check for reward line
        line_id = applicable_line.id
        applicable_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == line_id)
        self.assertFalse(reward_line, "reward line is not deleted")
        self.assertEqual(order_id.amount_total, 100.00, "Total amount is incorrect")
        product_line.unlink()
        self.assertEqual(order_id.amount_total, 0.00, "Total amount is incorrect")
