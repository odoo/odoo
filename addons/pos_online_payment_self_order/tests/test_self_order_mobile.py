
import odoo.tests
from odoo import Command

from odoo.addons.pos_online_payment.tests.online_payment_common import (
    OnlinePaymentCommon,
)
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderMobile(SelfOrderCommonTest, OnlinePaymentCommon):

    _test_user_groups = None  # FIXME list needed groups

    def _fake_online_payment(self, pos_order_id, access_token, expected_payment_provider_id, exit_route=None, confirmation_page=True):
        res = super()._fake_online_payment(pos_order_id, access_token, expected_payment_provider_id, exit_route=exit_route, confirmation_page=confirmation_page)
        self.env.ref('payment.cron_post_process_payment_tx').method_direct_trigger()  # Cron triggered in _handle_notification_data()
        return res

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.payment_provider = cls.provider

        cls.payment_provider_old_company_id = cls.payment_provider.company_id.id
        cls.payment_provider_old_journal_id = cls.payment_provider.journal_id.id
        cls.payment_provider.write({
            'company_id': cls.company.id,
        })
        cls.online_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Online payment',
            'type': 'online',
            'online_payment_provider_ids': [Command.set([cls.payment_provider.id])],
        })
        # Needed to test online payments through the portal
        cls.env['account.payment.method'].sudo().create({
            'name': 'Dummy method',
            'code': 'none',
            'payment_type': 'inbound'
        })

    def test_online_payment_self_pay_after_meal_table(self):
        """
        Verify that we can make multiple orders with online payment in self ordering mode
        with pay after meal and service mode table.
        """
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'table',
            'self_order_online_payment_method_id': self.online_payment_method.id,
        })
        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "table_ids": [(0, 0, {
                "table_number": 1,
            })],
        })
        self.pos_config.write({
            'self_ordering_pay_after': 'meal',
            'self_ordering_mode': 'mobile',
            'floor_ids': [(6, 0, [floor.id])],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_mobile_online_payment_meal")

        self_route_table = self.pos_config._get_self_order_route(floor.table_ids[0].id)
        self.start_tour(self_route_table, "self_mobile_online_payment_meal_table")

    def test_online_payment_self_dynamic_qr(self):
        """
        Verify that we can pay online after joining a dynamic_qr order via its order-specific URL.
        """
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'meal',
            'self_ordering_service_mode': 'dynamic_qr',
            'self_order_online_payment_method_id': self.online_payment_method.id,
        })
        floor = self.env["restaurant.floor"].create({
            "name": 'Main Floor',
            "table_ids": [(0, 0, {
                "table_number": 1,
            })],
        })
        self.pos_config.write({
            'floor_ids': [(6, 0, [floor.id])],
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        table = floor.table_ids[0]
        order = self.env['pos.order'].create({
            'session_id': self.pos_config.current_session_id.id,
            'table_id': table.id,
            'preset_id': self.in_preset.id,
            'amount_total': 0.0,
            'amount_tax': 0.0,
            'amount_return': 0.0,
            'amount_paid': 0.0,
        })
        order._ensure_access_token()
        self_route_order = self.pos_config._get_self_order_route(order=order)
        self.start_tour(self_route_order, "self_mobile_online_payment_meal_dynamic_qr")

    def test_online_payment_kiosk_qr_code(self):
        """
        Verify that when making an order from kiosk with online payment, a QR code is generated
        """
        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_service_mode': 'counter',
            'payment_method_ids': [Command.set(self.online_payment_method.ids)],
            'use_presets': False,
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_online_payment_kiosk_qr_code")

    def test_online_payment_mobile_self_order_preparation_changes(self):
        """
        Ensure that the Order button in the POS UI remains enabled when an online payment method
        is configured for mobile self-ordering and the order has not yet been paid.
        """
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_ordering_service_mode': 'table',
            'self_order_online_payment_method_id': self.online_payment_method.id,
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")

        # create self-order from mobile
        self.start_tour(self.pos_config._get_self_order_route(), 'test_online_payment_mobile_self_order_preparation_changes')
        order = self.pos_config.current_session_id.order_ids[0]
        self.assertEqual(order.state, 'draft')
        self.assertEqual(len(order.lines), 2)

        # Check self-order in pos-terminal order button remains enabled
        self.start_tour('/pos/ui?config_id=%d' % self.pos_config.id, 'test_online_payment_pos_self_order_preparation_changes', login='pos_user')

    def test_kiosk_cart_restore_and_cancel(self):
        """
        Verify that the cart restores correctly after back navigation from payment
        and that order cancellation works as expected.
        """

        self.pos_config.write({
            'self_ordering_mode': 'kiosk',
            'self_ordering_pay_after': 'each',
            'payment_method_ids': [Command.set(self.online_payment_method.ids)],
            'use_presets': False,
        })

        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "test_kiosk_cart_restore_and_cancel")

        kiosk_order = self.env['pos.order'].search(
            [('config_id', '=', self.pos_config.id)],
            order="id desc", limit=1
        )
        self.assertEqual(kiosk_order.state, 'cancel')

        # Collect order lines in a dict by product name
        order_lines = {line.product_id.name: line for line in kiosk_order.lines}
        self.assertEqual(len(order_lines), 2, "There should be exactly 2 order lines")

        coca_line = order_lines.get("Coca-Cola")
        self.assertIsNotNone(coca_line, "Expected order line not found")
        self.assertEqual(coca_line.qty, 1, "Order line quantity mismatch")

        fanta_line = order_lines.get("Fanta")
        self.assertIsNotNone(fanta_line, "Expected order line not found")
        self.assertEqual(fanta_line.qty, 1, "Order line quantity mismatch")

    def test_self_order_tip_amount_matches_backend(self):
        """
        Verify that the tip amount and order total match between the frontend
        and backend, with and without taxes on the tip product.
        """
        self.pos_config.iface_tipproduct = True
        tip_product = self.env.ref("point_of_sale.product_product_tip")
        self.pos_config.write({
            "self_ordering_mode": "mobile",
            "self_ordering_pay_after": "each",
            "use_presets": False,
            "tip_product_id": tip_product.id,
            'self_order_online_payment_method_id': self.online_payment_method.id,
        })
        tip_product.taxes_id = [(6, 0, self.default_tax15.ids)]
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        # With 15% default tax on tip product
        self.start_tour(self.pos_config._get_self_order_route(), "self_order_tip_amount_with_tax")
        order = self.pos_config.current_session_id.order_ids[0]
        tip_line = order.lines.filtered(lambda line: line.product_id == tip_product)
        self.assertEqual(tip_line.price_unit, 0.38)
        self.assertEqual(order.amount_total, 2.97)
        # Without tax on tip
        tip_product.taxes_id = False
        self.start_tour(self.pos_config._get_self_order_route(), "self_order_tip_amount_without_tax")
        order = self.pos_config.current_session_id.order_ids[0]
        tip_line = order.lines.filtered(lambda line: line.product_id == tip_product)
        self.assertEqual(tip_line.price_unit, 0.38)
        self.assertEqual(order.amount_total, 2.91)
