# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.addons.pos_online_payment.tests.online_payment_common import OnlinePaymentCommon
from odoo.addons.pos_restaurant.tests.test_frontend import TestFrontendCommon
from odoo.addons.pos_self_order.tests.self_order_common_test import SelfOrderCommonTest
from unittest.mock import patch
from odoo.addons.http_routing.models import ir_http
from odoo.addons.pos_online_payment.controllers.payment_portal import PaymentPortal

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

    def test_02_online_payment_with_multi_website_company(self):
        if not self.env["ir.module.module"].search([("name", "=", "website"), ("state", "=", "installed")]):
            self.skipTest("The 'website' module is required for this test.")

        # Setup another company and related POS configuration
        company_b_data = self.setup_other_company(name='Company B')
        company_b = company_b_data['company']

        provider_b = self.env['payment.provider'].create(
            {'name': 'Dummy provider B',
             'company_id': company_b.id,
             'state': 'test',
             'is_published': True,
             'payment_method_ids': [Command.set([self.pm_unknown.id])],
             })

        online_payment_method = self.env['pos.payment.method'].create({
            'name': 'Online payment B',
            'is_online_payment': True,
            'company_id': company_b.id,
            'online_payment_provider_ids': [Command.set([provider_b.id])],
        })

        test_sale_journal = company_b_data['default_journal_sale']
        pos_config = self.env['pos.config'].create({
            'name': 'Restaurant 2',
            'module_pos_restaurant': True,
            'company_id': company_b.id,
            'journal_id': test_sale_journal.id,
            'invoice_journal_id': test_sale_journal.id,
            'payment_method_ids': [Command.set([online_payment_method.id])],
            'self_ordering_mode': 'mobile',
            'self_ordering_pay_after': 'each',
            'self_order_online_payment_method_id': online_payment_method.id,
            'use_presets': False,
        })
        self.pos_admin.company_ids = [Command.link(company_b.id)]
        pos_config.with_user(self.pos_admin).open_ui()

        pos_config.current_session_id.set_opening_control(0, "")
        self.env.ref('base.user_admin').write({
            'company_ids': [Command.link(company_b.id)],
        })

        website_b = self.env['website'].create({
            'name': 'Website Test 2',
            'company_id': company_b.id,
        })

        # Create test user for the "first" company
        self.env['res.users'].create({
            'group_ids': [Command.set([self.ref('base.group_user')])],
            'name': 'Test User',
            'login': 'testuser',
            'password': 'testuser',
        })

        original_frontend_pre_dispatch = ir_http.IrHttp._frontend_pre_dispatch

        def patched_frontend_pre_dispatch(cls):
            self.env.ref('base.public_user')
            website_b.button_go_website()  # Simulate visiting Website B (populating request session data)
            original_frontend_pre_dispatch.__func__(cls)

        with patch.object(ir_http.IrHttp, '_frontend_pre_dispatch', classmethod(patched_frontend_pre_dispatch)):
            # Create a new order
            self.start_tour(pos_config._get_self_order_route(), "test_online_payment_self_multi_company", login="testuser")
            draft_order = self.env['pos.order'].search([('state', '=', 'draft')], limit=1)
            payment_route = PaymentPortal._get_pay_route(draft_order.id, draft_order.access_token)

            # Test payment page access for different users
            self.start_tour(payment_route, "test_online_payment_self_multi_company_payment", login="testuser")
            self.start_tour(payment_route, "test_online_payment_self_multi_company_payment", login="admin")
            self.start_tour(payment_route, "test_online_payment_self_multi_company_payment")
