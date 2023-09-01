# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

import odoo.tests
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_online_payment.models.pos_payment_method import PosPaymentMethod


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFrontendMobile(SelfOrderCommonTest):

    def _test_self_order_tour(self, self_order_pay_after, tour_name):
        self.pos_config.self_order_table_mode = True
        self.self_order_online_payment_method_id = self.env['pos.payment.method'].sudo()._get_or_create_online_payment_method(self.pos_config.company_id.id, self.pos_config.id)
        self.fake_provider = self.env['payment.provider'].create({
            'name': 'SelfOrderTest',
        })

        real_get_online_payment_providers = PosPaymentMethod._get_online_payment_providers
        def _fake_get_online_payment_providers(method_self, pos_config_id=False, error_if_invalid=True):
            if method_self.id == self.self_order_online_payment_method_id.id:
                return self.fake_provider
            else:
                return real_get_online_payment_providers(method_self, pos_config_id, error_if_invalid)

        with patch.object(PosPaymentMethod, '_get_online_payment_providers', _fake_get_online_payment_providers):
            self.pos_config.update({
                'self_order_pay_after': self_order_pay_after,
                'self_order_online_payment_method_id': self.self_order_online_payment_method_id,
            })
            self.pos_config.with_user(self.pos_user).open_ui()

            self.start_tour(
                self.pos_config._get_self_order_route(),
                tour_name,
                login=None,
            )

        self.fake_provider.unlink()

    def test_self_order_pay_after_each_tour(self):
        self._test_self_order_tour('each', 'pos_online_payment_self_order_after_each_cart_tour')

    def test_self_order_pay_after_meal_tour(self):
        self._test_self_order_tour('meal', 'pos_online_payment_self_order_after_meal_cart_tour')
