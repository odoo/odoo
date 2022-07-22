# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponNumbersCommon
from odoo.addons.website.tools import MockRequest
from odoo.addons.website_sale_loyalty.controllers.main import WebsiteSale
from odoo.tests import tagged
from odoo.tests.common import HttpCase


@tagged('-at_install', 'post_install')
class TestSaleCouponApplyPending(HttpCase, TestSaleCouponNumbersCommon):

    def setUp(self):
        super().setUp()

        self.WebsiteSaleController = WebsiteSale()

        self.website = self.env['website'].browse(1)
        self.global_program = self.p1
        self.coupon_program = self.env['loyalty.program'].create({
            'name': 'One Free Product',
            'program_type': 'coupons',
            'rule_ids': [(0, 0, {
                'minimum_qty': 2,
            })],
            'reward_ids': [(0, 0, {
                'reward_type': 'product',
                'reward_product_id': self.largeCabinet.id,
            })]
        })
        self.env['loyalty.generate.wizard'].with_context(active_id=self.coupon_program.id).create({
            'coupon_qty': 1,
            'points_granted': 1,
        }).generate_coupons()
        self.coupon = self.coupon_program.coupon_ids[0]

    def test_01_activate_coupon_with_existing_program(self):
        order = self.empty_order

        with MockRequest(self.env, website=self.website, sale_order_id=order.id, website_sale_current_pl=1) as request:
            self.WebsiteSaleController.cart_update_json(self.largeCabinet.id, set_qty=2)
            self.WebsiteSaleController.pricelist(self.global_program.rule_ids.code)
            self.assertEqual(order.amount_total, 576, "The order total should equal 576: 2*320 - 10% discount ")
            self.assertEqual(len(order.order_line), 2, "There should be 2 lines 1 for the product and 1 for the discount")

            self.WebsiteSaleController.activate_coupon(self.coupon.code)
            promo_code = request.session.get('pending_coupon_code')
            self.assertFalse(promo_code, "The promo code should be removed from the pending coupon dict")
            self.assertEqual(order.amount_total, 576, "The order total should equal 576: 2*320 - 0 (free product) - 10%")
            self.assertEqual(len(order.order_line), 3, "There should be 3 lines 1 for the product, 1 for the free product and 1 for the discount")

    def test_02_pending_coupon_with_existing_program(self):
        order = self.empty_order

        with MockRequest(self.env, website=self.website, sale_order_id=order.id, website_sale_current_pl=1) as request:
            self.WebsiteSaleController.cart_update_json(self.largeCabinet.id, set_qty=1)
            self.WebsiteSaleController.pricelist(self.global_program.rule_ids.code)
            self.assertEqual(order.amount_total, 288, "The order total should equal 288: 320 - 10%")

            self.WebsiteSaleController.activate_coupon(self.coupon.code)
            promo_code = request.session.get('pending_coupon_code')
            self.assertEqual(order.amount_total, 288, "The order total should still equal 288 as the coupon for free product can't be applied since it requires 2 min qty")
            self.assertEqual(promo_code, self.coupon.code, "The promo code should be set in the pending coupon dict as it couldn't be applied, we save it for later reuse")

            self.WebsiteSaleController.cart_update_json(self.largeCabinet.id, add_qty=1)
            promo_code = request.session.get('pending_coupon_code')
            self.assertFalse(promo_code, "The promo code should be removed from the pending coupon dict as it should have been applied")
            self.assertEqual(order.amount_total, 576, "The order total should equal 576: 2*320 - 0 (free product) - 10%")
