# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale_coupon.tests.test_program_numbers import TestSaleCouponProgramNumbers
from odoo.addons.website.tools import MockRequest
from odoo.exceptions import UserError
from odoo.tests import tagged


@tagged('-at_install', 'post_install')
class TestSaleCouponMultiwebsite(TestSaleCouponProgramNumbers):

    def setUp(self):
        super(TestSaleCouponMultiwebsite, self).setUp()
        self.website = self.env['website'].browse(1)
        self.website2 = self.env['website'].create({'name': 'website 2'})

    def test_01_multiwebsite_checks(self):
        """ Ensure the multi website compliance of programs and coupons, both in
            backend and frontend.
        """
        order = self.empty_order
        self.env['sale.order.line'].create({
            'product_id': self.largeCabinet.id,
            'name': 'Large Cabinet',
            'product_uom_qty': 2.0,
            'order_id': order.id,
        })

        def _remove_reward():
            order.order_line.filtered('is_reward_line').unlink()
            self.assertEqual(len(order.order_line.ids), 1, "Program should have been removed")

        def _apply_code(code, backend=True):
            if backend:
                self.env['sale.coupon.apply.code'].with_context(active_id=order.id).create({
                    'coupon_code': code
                }).process_coupon()
            else:
                self.env['sale.coupon.apply.code'].sudo().apply_coupon(order, code)

        # ==========================================
        # ========== Programs (with code) ==========
        # ==========================================

        # 1. Backend - Generic
        _apply_code(self.p1.promo_code)
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program")
        _remove_reward()

        # 2. Frontend - Generic
        with MockRequest(self.env, website=self.website):
            _apply_code(self.p1.promo_code, False)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program (2)")
            _remove_reward()

        # make program specific
        self.p1.website_id = self.website.id
        # 3. Backend - Specific
        with self.assertRaises(UserError):
            _apply_code(self.p1.promo_code)  # the order has no website_id so not possible to use a website specific code

        # 4. Frontend - Specific - Correct website
        order.website_id = self.website.id
        with MockRequest(self.env, website=self.website):
            _apply_code(self.p1.promo_code, False)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a specific promo program for the correct website")
            _remove_reward()

        # 5. Frontend - Specific - Wrong website
        self.p1.website_id = self.website2.id
        with MockRequest(self.env, website=self.website):
            _apply_code(self.p1.promo_code, False)
            self.assertEqual(len(order.order_line.ids), 1, "Should not get the reward as wrong website")

        # ==============================
        # =========== Coupons ==========
        # ==============================

        order.website_id = False
        self.env['coupon.generate.wizard'].with_context(active_id=self.discount_coupon_program.id).create({
            'nbr_coupons': 4,
        }).generate_coupon()
        coupons = self.discount_coupon_program.coupon_ids

        # 1. Backend - Generic
        _apply_code(coupons[0].code)
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic coupon program")
        _remove_reward()

        # 2. Frontend - Generic
        with MockRequest(self.env, website=self.website):
            _apply_code(coupons[1].code, False)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic coupon program (2)")
            _remove_reward()

        # make program specific
        self.discount_coupon_program.website_id = self.website.id
        # 3. Backend - Specific
        with self.assertRaises(UserError):
            _apply_code(coupons[2].code)  # the order has no website_id so not possible to use a website specific code

        # 4. Frontend - Specific - Correct website
        order.website_id = self.website.id
        with MockRequest(self.env, website=self.website):
            _apply_code(coupons[2].code, False)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a specific coupon program for the correct website")
            _remove_reward()

        # 5. Frontend - Specific - Wrong website
        self.discount_coupon_program.website_id = self.website2.id
        with MockRequest(self.env, website=self.website):
            _apply_code(coupons[3].code, False)
            self.assertEqual(len(order.order_line.ids), 1, "Should not get the reward as wrong website")

        # ========================================
        # ========== Programs (no code) ==========
        # ========================================

        order.website_id = False
        self.p1.website_id = False
        self.p1.promo_code = False
        self.p1.promo_code_usage = 'no_code_needed'

        # 1. Backend - Generic
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program")

        # 2. Frontend - Generic
        with MockRequest(self.env, website=self.website):
            order.recompute_coupon_lines()
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program (2)")

        # make program specific
        self.p1.website_id = self.website.id
        # 3. Backend - Specific
        order.recompute_coupon_lines()
        self.assertEqual(len(order.order_line.ids), 1, "The order has no website_id so not possible to use a website specific code")

        # 4. Frontend - Specific - Correct website
        order.website_id = self.website.id
        with MockRequest(self.env, website=self.website):
            order.recompute_coupon_lines()
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a specific promo program for the correct website")

        # 5. Frontend - Specific - Wrong website
        self.p1.website_id = self.website2.id
        with MockRequest(self.env, website=self.website):
            order.recompute_coupon_lines()
            self.assertEqual(len(order.order_line.ids), 1, "Should not get the reward as wrong website")
