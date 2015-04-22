# -*- coding: utf-8 -*-
from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon


class TestSaleCoupon(TestSaleCouponCommon):
    def test_sale_coupon_type(self):

        order_id = self.SaleOrder.create({
            'partner_id': self.partner_id.id})

        ######### Public unique code - Buy 1 shoe + get 1 socks free
        order_id.write({'order_line': [(0, 0, {'product_id': self.product_shoe.id, 'product_uom_qty': 1})]})
        applicable_line = order_id.order_line.filtered(lambda x: x.product_id == self.product_shoe)
        reward_line = order_id.order_line.filtered(lambda x: x.product_id == self.reward_product and x.generated_from_line_id.id is applicable_line)
        self.assertFalse(reward_line, "Reward line is created before entering the code")
        wizard = self.SaleGetCoupon.create({'textbox_coupon_code': 'ODOO_AAAA'})
        print "<<<<<<<>>>>", wizard.process_coupon()
