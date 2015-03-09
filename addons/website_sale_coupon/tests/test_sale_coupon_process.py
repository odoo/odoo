# -*- coding: utf-8 -*-
import datetime

from openerp.addons.website_sale_coupon.tests.common import TestSaleCouponCommon
from openerp.exceptions import AccessError, ValidationError, Warning


class TestSaleCoupon(TestSaleCouponCommon):

    def test_sale_coupon_type(self):

        # In order to test create sale order and confirmed it.
        #Buy 2 get 1 free
        order_id1 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_conference.id, 'product_uom_qty': 3})]
        })
        order_id1.apply_coupon()
        order_id1.action_button_confirm()
        self.assertEqual(
            order_id1.amount_untaxed, 2.0, 'Coupon Code: Coupon Code not Apply')

        # 10% Discount on Product
        order_id2 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_training.id})]
        })
        order_id2.apply_coupon()
        order_id2.action_button_confirm()
        self.assertEqual(
            order_id2.amount_untaxed, 900.0, 'Coupon Code: Coupon Code not Apply')

        #Buy 1 product get another product free
        order_id3 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_training.id}),
                           (0, 0, {'product_id': self.product_conference.id})]
        })
        order_id3.apply_coupon()
        order_id3.action_button_confirm()
        self.assertEqual(
            order_id3.amount_untaxed, 1000.0, 'Coupon Code: Coupon Code not Apply')

        #minimum purchase of 1000 and get 100 off on cart
        order_id4 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_technical_training.id})]
        })
        order_id4.apply_coupon()
        order_id4.action_button_confirm()
        self.assertEqual(
            order_id4.amount_untaxed, 1400.0, 'Coupon Code: Coupon Code not Apply')

        #use 'SC5657585' to get 10 % discount
        order_id5 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_training.id})]
        })
        order_id5.apply_coupon('SC5657585')
        order_id5.action_button_confirm()
        self.assertEqual(
            order_id5.amount_untaxed, 900.0, 'Coupon Code: Coupon Code not Apply')

        #use 'SC5656565' and get 30% on chepest product in cart befor tomorrow
        order_id6 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_training.id}),
                           (0, 0, {'product_id': self.product_technical_training.id})]
        })
        order_id6.apply_coupon('SC5656565')
        order_id6.action_button_confirm()
        self.assertEqual(
            order_id6.amount_untaxed, 2200.0, 'Coupon Code: Coupon Code not Apply')

        #on minimum purchase >= 2000 and get dicount coupon of 500
        order_id7 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_training.id}),
                           (0, 0, {'product_id': self.product_technical_training.id})]
        })
        order_id7.apply_coupon()
        order_id7.action_button_confirm()
        coupon = self.SaleCoupon.search(
            [('origin_order_id', '=', order_id7.id)])
        self.assertTrue(
            coupon, 'SaleCoupon: Creation of Coupon failed.')

        # using code get 500 off
        order_id8 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_technical_training.id})]
        })
        order_id8.apply_coupon(coupon.coupon_code)
        order_id8.action_button_confirm()
        self.assertEqual(
            order_id8.amount_untaxed, 1000.0, 'Coupon Code: Coupon Code not Apply')

        # free shipping
        order_id9 = self.SaleOrder.create({
            'partner_id': self.partner_id.id,
            'date_order': datetime.datetime.now(),
            'order_line': [(0, 0, {'product_id': self.product_event.id})]
        })
        order_id9.apply_coupon()
        order_id9.action_button_confirm()
        self.assertEqual(
            order_id9.amount_untaxed, 700.0, 'Coupon Code: Coupon Code not Apply')
