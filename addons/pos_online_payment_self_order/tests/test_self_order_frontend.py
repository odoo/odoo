# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

import odoo.tests
from odoo import Command
from odoo.addons.mail.tests.common import mail_new_test_user
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
# from odoo.addons.pos_online_payment.models.pos_payment_method import PosPaymentMethod


@odoo.tests.tagged("post_install", "-at_install")
class TestSelfOrderFrontendMobile(SelfOrderCommonTest):
    pass

@odoo.tests.tagged("post_install", "-at_install")
class TestUi(OnlinePaymentCommon):
    def _get_url(self):
        return f"/pos/ui?config_id={self.pos_config.id}"

    def start_pos_tour(self, tour_name, login="pos_admin", **kwargs):
        self.start_tour(self._get_url(), tour_name, login=login, **kwargs)

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
        cls.sales_journal = cls.env['account.journal'].create({
            'name': 'Sales Journal for POS OP Test',
            'code': 'POPSJ',
            'type': 'sale',
            'company_id': cls.company.id
        })
        cls.pos_config = cls.env['pos.config'].create({
            'name': 'POS OP Test Shop',
            'module_pos_restaurant': True,
            'invoice_journal_id': cls.sales_journal.id,
            'journal_id': cls.sales_journal.id,
            'payment_method_ids': [Command.link(cls.online_payment_method.id)],
        })
        main_floor = cls.env['restaurant.floor'].create({
            'name': 'Main Floor',
            'pos_config_ids': [(4, cls.pos_config.id)],
            'floor_prefix': 1,
        })
        cls.main_floor_table_1 = cls.env['restaurant.table'].create([{
            'table_number': 101,
            'floor_id': main_floor.id,
            'seats': 4,
            'position_h': 100,
            'position_v': 100,
        }])
        cls.env['restaurant.table'].create([{
            'table_number': 102,
            'floor_id': main_floor.id,
            'seats': 4,
            'shape': 'square',
            'position_h': 350,
            'position_v': 100,
        }])
        cls.pos_admin = mail_new_test_user(
            cls.env,
            groups="base.group_user,point_of_sale.group_pos_manager",
            login="pos_admin",
            name="POS Admin",
            tz="Europe/Brussels",
        )


class TestSelfOrderOnlinePayment(TestUi):
    def test_01_online_payment_with_multi_table(self):
        self.pos_config.with_user(self.pos_admin).open_ui()
        self.start_pos_tour('OnlinePaymentWithMultiTables', login="pos_admin")
