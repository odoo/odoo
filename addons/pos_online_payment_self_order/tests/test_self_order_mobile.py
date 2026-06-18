
import odoo.tests
from odoo import Command

from odoo.addons.pos_online_payment.tests.online_payment_common import (
    OnlinePaymentCommon,
)
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderMobile(SelfOrderCommonTest, OnlinePaymentCommon):

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
            'is_online_payment': True,
            'online_payment_provider_ids': [Command.set([cls.payment_provider.id])],
        })
        # Needed to test online payments through the portal
        cls.env['account.payment.method'].sudo().create({
            'name': 'Dummy method',
            'code': 'none',
            'payment_type': 'inbound'
        })
