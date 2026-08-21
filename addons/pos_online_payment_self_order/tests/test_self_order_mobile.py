
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
