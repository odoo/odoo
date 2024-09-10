# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import timedelta

import odoo.tests
from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.fields import Datetime

from .common import TestWebsiteEventSaleCommon


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo, TestWebsiteEventSaleCommon):
    def setUp(self):
        super().setUp()

        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.env.ref('payment.payment_provider_transfer').write({
            'state': 'enabled',
            'is_published': True,
        })

        cls.event_2 = cls.env['event.event'].create({
            'name': 'Conference for Architects TEST',
            'user_id': cls.env.ref('base.user_admin').id,
            'date_begin': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'date_end': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 16:30:00'),
            'website_published': True,
        })

        cls.env['event.event.ticket'].create([{
            'name': 'Standard',
            'event_id': cls.event_2.id,
            'product_id': cls.env.ref('event_product.product_product_event').id,
            'start_sale_datetime': (Datetime.today() - timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'end_sale_datetime': (Datetime.today() + timedelta(90)).strftime('%Y-%m-%d'),
            'price': 1000.0,
        }, {
            'name': 'VIP',
            'event_id': cls.event_2.id,
            'product_id': cls.env.ref('event_product.product_product_event').id,
            'end_sale_datetime': (Datetime.today() + timedelta(90)).strftime('%Y-%m-%d'),
            'price': 1500.0,
        }])

        cls.event_3 = cls.env['event.event'].create({
            'name': 'Last ticket test',
            'user_id': cls.env.ref('base.user_admin').id,
            'date_begin': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'date_end': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 16:30:00'),
            'website_published': True,
        })

        cls.env['event.event.ticket'].create([{
            'name': 'VIP',
            'event_id': cls.event_3.id,
            'product_id': cls.env.ref('event_product.product_product_event').id,
            'end_sale_datetime': (Datetime.today() + timedelta(90)).strftime('%Y-%m-%d'),
            'price': 1500.0,
            'seats_max': 2,
        }])

        # flush event to ensure having tickets available in the tests
        cls.env.flush_all()

        (cls.env.ref('base.partner_admin') + cls.partner_demo).write({
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': cls.env.ref('base.us').id,
            'state_id': cls.env.ref('base.state_us_39').id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })

        cls.env['account.journal'].create({'name': 'Cash - Test', 'type': 'cash', 'code': 'CASH - Test'})

    def test_admin(self):
        self.env['product.pricelist'].with_context(active_test=False).search([]).unlink()
        # Seen that:
        # - this test relies on demo data that are entirely in USD (pricelists)
        # - that main demo company is gelocated in US
        # - that this test awaits for hardcoded USDs amount
        # we have to force company currency as USDs only for this test
        self.cr.execute("UPDATE res_company SET currency_id = %s WHERE id = %s", [self.env.ref('base.USD').id, self.env.ref('base.main_company').id])
        self.env['product.pricelist'].create({'name': "Public Pricelist"})

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/", 'event_buy_tickets', login="admin")

    def test_demo(self):
        self.env['product.pricelist'].with_context(active_test=False).search([]).unlink()
        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        #  Ensure the use of USD (company currency)
        self.env['product.pricelist'].create({'name': "Public Pricelist"})

        self.start_tour("/", 'event_buy_tickets', login="demo")

    def test_buy_last_ticket(self):
        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/", 'event_buy_last_ticket')

    def test_pricelists_different_currencies(self):
        self.env.user.groups_id += self.env.ref('product.group_product_pricelist')
        self.start_tour("/", 'event_sale_pricelists_different_currencies', login='admin')
    # TO DO - add public test with new address when convert to web.tour format.
