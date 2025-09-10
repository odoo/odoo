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
            "module_pos_restaurant": True,
            "payment_method_ids": [Command.set([cls.online_payment_method.id])],
            "self_order_online_payment_method_id": cls.online_payment_method.id,
        })
        cls.simple_accountman.group_ids = cls.env.ref('point_of_sale.group_pos_user')


class TestSelfOrderOnlinePayment(TestUi):
    @mute_logger('odoo.addons.point_of_sale.models.pos_order')
    def test_01_self_order_refund_through_online_payment(self):
        def _send_refund_request(self):
            return
        with patch.object(self.env.registry['payment.transaction'], '_send_refund_request', _send_refund_request):
            order = self._open_session_fake_cashier_unpaid_order(self.coca_cola_test)
            order.source = 'mobile'
            op_data = order.with_user(self.simple_accountman).get_and_set_online_payments_data(order.amount_total)
            self.assertEqual(op_data['id'], order.id)
            self.assertTrue('paid_order' not in op_data)
            self._fake_online_payment(order.id, order.access_token, self.payment_provider.id)
            self.assertEqual(order.state, 'paid', "Order should be marked as paid after online payment.")
            self.start_pos_tour('test_pos_self_order_refund_through_online_payment', login='accountman')
