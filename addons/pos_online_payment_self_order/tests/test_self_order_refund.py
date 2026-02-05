# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.addons.pos_online_payment.tests.test_frontend import TestUi as PosOnlinePaymentCommon
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon
from unittest.mock import patch
from odoo.tools import mute_logger


@odoo.tests.tagged("post_install", "-at_install")
class TestUi(TestFrontendCommon, PosOnlinePaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_provider = cls.provider  # The dummy_provider used by the tests of the 'payment' module.
        cls.payment_provider_old_company_id = cls.payment_provider.company_id.id
        cls.payment_provider_old_journal_id = cls.payment_provider.journal_id.id
        cls.payment_provider.write({
            'company_id': cls.company.id,
        })
        cls.online_payment_method = cls.env['pos.payment.method'].create({
            'name': 'Online payment',
            'is_online_payment': True,
            'online_payment_provider_ids': [Command.set([cls.payment_provider.id])],
        })
        cls.pos_config.write({
            'module_pos_restaurant': True,
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_order_online_payment_method_id': cls.online_payment_method.id,
        })
        cls.simple_accountman.group_ids = cls.env.ref('point_of_sale.group_pos_user')


class TestSelfOrderOnlinePayment(TestUi):
    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_pos_self_order_refund_through_online_payment(self):
        def _send_refund_request(self):
            return
        with patch.object(self.env.registry['payment.transaction'], '_send_refund_request', _send_refund_request):
            self.pos_config.with_user(self.pos_user).open_ui()
            self.pos_config.current_session_id.set_opening_control(0, "")
            self_route = self.pos_config._get_self_order_route()
            self.start_tour(self_route, 'create_self_order')
            order = self.pos_config.current_session_id.order_ids[0]
            self._fake_online_payment(order.id, order.access_token, self.payment_provider.id, exit_route="/")
            self.assertEqual(order.state, 'paid', "Order should be marked as paid after online payment.")
            self.start_pos_tour('test_pos_self_order_refund_through_online_payment', login='accountman')
