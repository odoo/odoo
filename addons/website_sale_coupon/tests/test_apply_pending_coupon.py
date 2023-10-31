# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_coupon.tests.test_program_numbers import TestSaleCouponProgramNumbers
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_coupon.controllers.main import WebsiteSale
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSaleCouponApplyPending(TestSaleCouponProgramNumbers):

    def setUp(self):
        super().setUp()

        self.WebsiteSaleController = WebsiteSale()

        self.website = self.env['website'].browse(1)
        self.global_program = self.p1
        self.coupon_program = self.env['coupon.program'].create({
            'name': 'One Free Product',
            'program_type': 'coupon_program',
            'rule_min_quantity': 2.0,
            'reward_type': 'product',
            'reward_product_id': self.largeCabinet.id,
            'active': True,
        })

        self.coupon = self.env['coupon.coupon'].create({
            'program_id': self.coupon_program.id,
        })

    def test_01_activate_coupon_with_existing_program(self):
        order = self.empty_order

        with MockRequest(self.env, website=self.website, sale_order_id=order.id, website_sale_current_pl=1) as request:
            self.WebsiteSaleController.cart_update_json(self.largeCabinet.id, set_qty=3)
            self.WebsiteSaleController.pricelist(self.global_program.promo_code)
            self.assertEqual(order.amount_total, 864, "The order total should equal 864: 3*320 - 10% discount ")

            self.WebsiteSaleController.activate_coupon(self.coupon.code)
            promo_code = request.session.get('pending_coupon_code')
            self.assertFalse(promo_code, "The promo code should be removed from the pending coupon dict")
            self.assertEqual(order.amount_total, 576, "The order total should equal 576: 3*320 - 320 (free product) - 10%")

    def test_02_pending_coupon_with_existing_program(self):
        order = self.empty_order

        with MockRequest(self.env, website=self.website, sale_order_id=order.id, website_sale_current_pl=1) as request:
            self.WebsiteSaleController.cart_update_json(self.largeCabinet.id, set_qty=1)
            self.WebsiteSaleController.pricelist(self.global_program.promo_code)
            self.assertEqual(order.amount_total, 288, "The order total should equal 288: 320 - 10%")

            self.WebsiteSaleController.activate_coupon(self.coupon.code)
            promo_code = request.session.get('pending_coupon_code')
            self.assertEqual(order.amount_total, 288, "The order total should still equal 288 as the coupon for free product can't be applied since it requires 2 min qty")
            self.assertEqual(promo_code, self.coupon.code, "The promo code should be set in the pending coupon dict as it couldn't be applied, we save it for later reuse")

            self.WebsiteSaleController.cart_update_json(self.largeCabinet.id, add_qty=2)
            promo_code = request.session.get('pending_coupon_code')
            self.assertFalse(promo_code, "The promo code should be removed from the pending coupon dict as it should have been applied")
            self.assertEqual(order.amount_total, 576, "The order total should equal 576: 3*320 - 320 (free product) - 10%")
