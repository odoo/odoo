
import odoo.tests
from odoo import Command
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest

@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderMobile(SelfOrderCommonTest, OnlinePaymentCommon):

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
        self.pos_config.write({
            'self_ordering_pay_after': 'meal',
        })
        self.pos_config.with_user(self.pos_user).open_ui()
        self.pos_config.current_session_id.set_opening_control(0, "")
        self_route = self.pos_config._get_self_order_route()
        self.start_tour(self_route, "self_mobile_online_payment_meal_table")

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
