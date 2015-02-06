# -*- coding: utf-8 -*-
import datetime
from dateutil.relativedelta import relativedelta

from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon
from openerp.exceptions import AccessError, ValidationError, Warning

class TestSaleCoupon(TestSaleCouponCommon):

    def test_sale_coupon_type(self):

        # In order to test create sale order and confirmed it.
        order_id1 = self.sale_order.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.conference_product.id, 'product_uom_qty':5})]
        })
        order_id1.action_button_confirm()
        order_id1.order_line.state = 'done'
        # on Confirm SO it creates a Pre sale Coupon with unique Coupon Code
        coupons = [coupon.code for order_line in order_id1.order_line for coupon in order_line.coupon_ids]
        self.assertEqual(
            len(coupons), 5, 'Coupon Code: Coupon Code not Apply')

        #product is not available on cart and apply coupon code .
        order_id2 = self.sale_order.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.training_product.id})]
        })

        order_id2.order_line.apply_coupon(
            order_id1.order_line.coupon_ids[0].code)
        order_id2.action_button_confirm()
        self.assertEqual(
            order_id2.amount_untaxed, 1.0, 'Coupon Code: Coupon Code not Apply')

        # one coupons apply on product
        order_id3 = self.sale_order.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.conference_product.id, 'product_uom_qty': 5})]
        })
        order_id3.order_line.apply_coupon(
            order_id1.order_line.coupon_ids[1].code)
        order_id3.action_button_confirm()
        self.assertEqual(
            order_id3.amount_untaxed, 4.0, 'Coupon Code: Coupon Code not Apply')

        # multiple coupon of same products
        order_id4 = self.sale_order.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.conference_product.id})]
        })

        order_id4.order_line.apply_coupon(
            order_id1.order_line.coupon_ids[2].code)
        order_id4.order_line.apply_coupon(
            order_id1.order_line.coupon_ids[3].code)
        order_id4.action_button_confirm()
        self.assertEqual(
            order_id4.amount_untaxed, 0.0, 'Coupon Code: Coupon Code not Apply')
