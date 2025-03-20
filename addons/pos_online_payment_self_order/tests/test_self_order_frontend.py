# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import odoo.tests
from odoo import Command
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_restaurant.tests.test_common import TestPoSRestaurantDataHttpCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFrontendMobile(SelfOrderCommonTest):
    pass

@odoo.tests.tagged("post_install", "-at_install")
class TestUi(TestPoSRestaurantDataHttpCommon, OnlinePaymentCommon):
    @classmethod
    def setUpClass(self):
        super().setUpClass()

        self.payment_provider = self.provider # The dummy_provider used by the tests of the 'payment' module.
        self.payment_provider_old_company_id = self.payment_provider.company_id.id
        self.payment_provider_old_journal_id = self.payment_provider.journal_id.id
        self.payment_provider.write({
            'company_id': self.company.id,
        })
        self.online_payment_method = self.env['pos.payment.method'].create({
            'name': 'Online payment',
            'is_online_payment': True,
            'online_payment_provider_ids': [Command.set([self.payment_provider.id])],
        })
        self.pos_config.write({
            "module_pos_restaurant": True,
            "payment_method_ids": [Command.set([self.online_payment_method.id])],
        })


class TestSelfOrderOnlinePayment(TestUi):
    def test_01_online_payment_with_multi_table(self):
        # No need to check preparation printer in this test.
        self.env["pos.printer"].search([]).unlink()
        self.start_pos_tour('OnlinePaymentWithMultiTables', login="pos_admin")
