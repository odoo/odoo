# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

import odoo.tests
from odoo.exceptions import ValidationError
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
# from odoo.addons.pos_online_payment.models.pos_payment_method import PosPaymentMethod


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFrontendMobile(SelfOrderCommonTest):

    def test_online_payment_method_needs_a_provider(self):
        self.env['payment.provider'].search([]).is_published = False
        online_payment_method = self.env['pos.payment.method'].create({
            'name': 'Online payment',
            'is_online_payment': True,
        })
        self.pos_config.write({
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
        })
        with self.assertRaises(ValidationError):
            self.pos_config.self_order_online_payment_method_id = online_payment_method
