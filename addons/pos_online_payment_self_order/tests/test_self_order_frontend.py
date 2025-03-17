# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

import odoo.tests
from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFrontendMobile(SelfOrderCommonTest):
    pass

@odoo.tests.tagged("post_install", "-at_install")
class TestUi(TestFrontendCommon, OnlinePaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.payment_provider = cls.provider # The dummy_provider used by the tests of the 'payment' module.

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
        })


class TestSelfOrderOnlinePayment(TestUi):
    def test_01_online_payment_with_multi_table(self):
        # No need to check preparation printer in this test.
        self.env["pos.printer"].search([]).unlink()
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour('OnlinePaymentWithMultiTables', login="pos_admin")
