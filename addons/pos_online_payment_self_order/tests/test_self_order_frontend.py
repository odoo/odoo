# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFrontendMobile(SelfOrderCommonTest, OnlinePaymentCommon):
    def test_kiosk_order_with_online_payment(self):
        """Verify that self ordering works when only an online payment method is configured."""

        self.provider.write({
            'company_id': self.company.id,
        })

        self.online_payment_method = self.env['pos.payment.method'].create({
            'name': 'Online payment',
            'is_online_payment': True,
            'online_payment_provider_ids': [(6, 0, [self.provider.id])],
        })

        self.pos_config.write({
            'self_ordering_takeaway': False,
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            "payment_method_ids": [(6, 0, [self.online_payment_method.id])],
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "tour_kiosk_online_payment_cart_check")

        # Ensure a POS order was created after the tour
        kiosk_order = self.env['pos.order'].search([('config_id', '=', self.pos_config.id)], order="id desc", limit=1)
        self.assertEqual(len(kiosk_order), 1, "No POS order was created")

        # Collect order lines in a dict by product name
        order_lines = {line.product_id.display_name: line for line in kiosk_order.lines}
        self.assertEqual(len(order_lines), 2, "There should be exactly 2 order lines")

        coca_line = order_lines.get("Coca-Cola")
        self.assertIsNotNone(coca_line, "Expected order line not found")
        self.assertEqual(coca_line.qty, 1, "Order line quantity mismatch")

        fanta_line = order_lines.get("Fanta")
        self.assertIsNotNone(fanta_line, "Expected order line not found")
        self.assertEqual(fanta_line.qty, 1, "Order line quantity mismatch")
