# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.sale_loyalty.tests.common import TestSaleCouponNumbersCommon
from odoo.addons.website.tools import MockRequest


@tagged('-at_install', 'post_install')
class TestSaleCouponMultiwebsite(TestSaleCouponNumbersCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.website = cls.env['website'].browse(1)
        cls.website2 = cls.env['website'].create({'name': 'website 2'})

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
            self._clear_rewards(order)
            self.assertEqual(len(order.order_line.ids), 1, "Program should have been removed")

        def _apply_code(code, backend=True):
            try:
                self._apply_promo_code(order, code)
            except UserError as e:
                if backend:
                    raise e

        # ==========================================
        # ========== Programs (with code) ==========
        # ==========================================

        # 1. Backend - Generic
        _apply_code(self.p1.rule_ids.code)
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program")
        _remove_reward()

        # 2. Frontend - Generic
        with MockRequest(self.env, website=self.website):
            _apply_code(self.p1.rule_ids.code, False)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program (2)")
            _remove_reward()

        # make program specific
        self.p1.website_id = self.website.id
        # 3. Backend - Specific - sale_ok disabled
        self.p1.sale_ok = False
        with self.assertRaises(UserError):
            _apply_code(self.p1.rule_ids.code)  # the program is not enabled for Sales (backend)

        # 3.5. Backend - Specific - sale_ok enabled
        self.p1.sale_ok = True
        _apply_code(self.p1.rule_ids.code)
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is enabled for Sales(backend)")
        _remove_reward()

        # 4. Frontend - Specific - Correct website
        order.website_id = self.website.id
        with MockRequest(self.env, website=self.website):
            _apply_code(self.p1.rule_ids.code, False)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a specific promo program for the correct website")
            _remove_reward()

        # 5. Frontend - Specific - Wrong website
        self.p1.website_id = self.website2.id
        with MockRequest(self.env, website=self.website):
            _apply_code(self.p1.rule_ids.code, False)
            self.assertEqual(len(order.order_line.ids), 1, "Should not get the reward as wrong website")

        # ==============================
        # =========== Coupons ==========
        # ==============================

        order.website_id = False
        self.env['loyalty.generate.wizard'].with_context(active_id=self.discount_coupon_program.id).create({
            'coupon_qty': 4,
            'points_granted': 1,
        }).generate_coupons()
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
        # 3. Backend - Specific - sale_ok disabled
        self.discount_coupon_program.sale_ok = False
        with self.assertRaises(UserError):
            _apply_code(coupons[2].code)  # the program is not enabled for Sales (backend)

        # 3.5. Backend - Specific - sale_ok enabled
        self.discount_coupon_program.sale_ok = True
        _apply_code(coupons[2].code)
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is enabled for Sales(backend)")
        _remove_reward()

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
        self.p1.rule_ids.code = False
        self.p1.trigger = 'auto'
        self.p1.rule_ids.mode = 'auto'

        # 1. Backend - Generic
        all_programs = self.env['loyalty.program'].search([])
        self._auto_rewards(order, all_programs)
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program")

        # 2. Frontend - Generic
        with MockRequest(self.env, website=self.website):
            self._auto_rewards(order, all_programs)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program (2)")

        # make program specific
        self.p1.website_id = self.website.id
        # 3. Backend - Specific
        self.p1.sale_ok = False
        self._auto_rewards(order, all_programs)
        self.assertEqual(len(order.order_line.ids), 1, "The program is not enabled for Sales (backend)")

        # 3.5. Backend - Specific - sale_ok enabled
        self.p1.sale_ok = True
        self._auto_rewards(order, all_programs)
        self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a generic promo program")

        # 4. Frontend - Specific - Correct website
        order.website_id = self.website.id
        with MockRequest(self.env, website=self.website):
            self._auto_rewards(order, all_programs)
            self.assertEqual(len(order.order_line.ids), 2, "Should get the discount line as it is a specific promo program for the correct website")

        # 5. Frontend - Specific - Wrong website
        self.p1.website_id = self.website2.id
        with MockRequest(self.env, website=self.website):
            self._auto_rewards(order, all_programs)
            self.assertEqual(len(order.order_line.ids), 1, "Should not get the reward as wrong website")
