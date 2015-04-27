# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

        ######### Buy 1 iphone + get discount coupon for 10% off on cart on purchase of 1 laptop
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_iphone.id, 'product_uom_qty': 1})]})
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_iphone)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id == applicable_line)
        self.assertFalse(reward_line, "Reward line is created before entering the code")
        order_id.order_line[0].button_confirm()
        self.assertTrue(order_id.generated_coupon_ids, "Coupon is not generated properly")
        # create another sales order
        order_id1 = self.SaleOrder.create({'partner_id': self.partner_id.id, 'order_line': [(0, 0, {'product_id': self.product_laptop.id, 'product_uom_qty': 1})]})
        order_id1.apply_coupon_reward('ODOO_INVALID')
