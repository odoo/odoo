# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

        # # #########buy any product in 2 qty of category beverage and get 2$ off
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pepsi.id, 'product_uom_qty': 2})]})
        product_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_pepsi)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertTrue(product_line, "Product line is not created")
        self.assertEqual(product_line.product_uom_qty, 2, "Reward product qty is invalid")
        self.assertEqual(reward_line.price_subtotal, -2, "Reward amount on category is incorrect")
        self.assertEqual(order_id.amount_total, 18, "Total amount is invalid")
        # #update the qty of product line, addition
        product_line.write({'product_uom_qty': 4})
        order_id.apply_immediately_reward()
        self.assertEqual(reward_line.price_subtotal, -2, "Reward amount on category is incorrect")
        self.assertEqual(order_id.amount_total, 38, "Total amount is invalid")
        #unlink the product line
        product_line.unlink()
        order_id.apply_immediately_reward()
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line)
        self.assertFalse(reward_line, "Reward is not deleting properly")
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")
        #add the new product line of coca cola
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_coca_cola.id})]})
        product_line1 = order_id.order_line.filtered(lambda x: x.product_id == self.product_coca_cola)
        reward_line1 = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line1)
        self.assertFalse(reward_line1)
        self.assertEqual(order_id.amount_total, 20, "Total amount is invalid")
        #add 1 product line of pepsi
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_pepsi.id})]})
        product_line2 = order_id.order_line.filtered(lambda x: x.product_id == self.product_pepsi)
        reward_line1 = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line2)
        reward_line2 = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == product_line1)
        self.assertEqual(order_id.amount_total, 30, "Total amount is invalid")
        self.assertFalse(reward_line1)
        self.assertFalse(reward_line2)
        product_line1.unlink()
        product_line2.unlink()
        reward_line1.unlink()
        reward_line2.unlink()
        reward_line.unlink()
        self.assertEqual(order_id.amount_total, 0, "Total amount is invalid")
