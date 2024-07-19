# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests

from datetime import timedelta

from odoo.addons.base.tests.common import HttpCaseWithUserDemo
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.payment.tests.http_common import PaymentHttpCommon
from odoo.tools import mute_logger
from odoo.fields import Datetime


@odoo.tests.common.tagged('post_install', '-at_install')
class TestUi(HttpCaseWithUserDemo, TestWebsiteEventSaleCommon):

    def setUp(self):
        super().setUp()

        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        self.env.ref('payment.payment_provider_transfer').write({
            'state': 'enabled',
            'is_published': True,
        })

        self.env['event.event.ticket'].create({
            'name': 'VIP',
            'event_id': self.event_2.id,
            'product_id': self.env.ref('event_sale.product_product_event').id,
            'end_sale_datetime': (Datetime.today() + timedelta(90)).strftime('%Y-%m-%d'),
            'price': 1500.0,
        })

        self.event_3 = self.env['event.event'].create({
            'name': 'Last ticket test',
            'user_id': self.env.ref('base.user_admin').id,
            'date_begin': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 07:00:00'),
            'date_end': (Datetime.today() + timedelta(days=5)).strftime('%Y-%m-%d 16:30:00'),
            'website_published': True,
        })

        self.env['event.event.ticket'].create([{
            'name': 'VIP',
            'event_id': self.event_3.id,
            'product_id': self.env.ref('event_sale.product_product_event').id,
            'end_sale_datetime': (Datetime.today() + timedelta(90)).strftime('%Y-%m-%d'),
            'price': 1500.0,
            'seats_max': 2,
        }])

        # flush event to ensure having tickets available in the tests
        self.env.flush_all()

        (self.env.ref('base.partner_admin') + self.partner_demo).write({
            'street': '215 Vine St',
            'city': 'Scranton',
            'zip': '18503',
            'country_id': self.env.ref('base.us').id,
            'state_id': self.env.ref('base.state_us_39').id,
            'phone': '+1 555-555-5555',
            'email': 'admin@yourcompany.example.com',
        })

        self.env['account.journal'].create({'name': 'Cash - Test', 'type': 'cash', 'code': 'CASH - Test'})

    def test_admin(self):
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

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
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

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
        if self.env['ir.module.module']._get('payment_custom').state != 'installed':
            self.skipTest("Transfer provider is not installed")

        transfer_provider = self.env.ref('payment.payment_provider_transfer')
        transfer_provider.write({
            'state': 'enabled',
            'is_published': True,
        })
        transfer_provider._transfer_ensure_pending_msg_is_set()

        self.start_tour("/", 'event_buy_last_ticket')

    def test_pricelists_different_currencies(self):
        self.start_tour("/", 'event_sale_pricelists_different_currencies', login='admin')
    # TO DO - add public test with new address when convert to web.tour format.


@odoo.tests.common.tagged('post_install', '-at_install')
class TestRoutes(HttpCaseWithUserDemo, TestWebsiteEventSaleCommon, PaymentHttpCommon):

    @mute_logger('odoo.http')
    def test_check_seats_avail_before_purchase(self):
        self.authenticate(None, None)

        so_line_1, so_line_2 = self.env['sale.order.line'].create([
            {
                'event_id': self.event.id,
                'event_ticket_id': self.ticket.id,
                'name': self.event.name,
                'order_id': self.so.id,
                'product_id': self.ticket.product_id.id,
                'product_uom_qty': 2,
            },
            {
                'event_id': self.event_2.id,
                'event_ticket_id': self.ticket_2.id,
                'name': self.event_2.name,
                'order_id': self.so.id,
                'product_id': self.ticket_2.product_id.id,
                'product_uom_qty': 2,
            },
        ])
        self.so._cart_update(line_id=so_line_1.id, product_id=self.ticket.product_id.id, set_qty=1)
        self.so._cart_update(line_id=so_line_2.id, product_id=self.ticket_2.product_id.id, set_qty=1)

        url = self._build_url(f'/shop/payment/transaction/{self.so.id}')
        self.assertEqual(self.event.seats_taken, 0)
        self.assertEqual(self.event_2.seats_taken, 0)
        self.env['event.registration'].create([
            {
                'event_id': self.event.id,
                'name': 'reg1',
                'state': 'done',
            },
            {
                'event_id': self.event_2.id,
                'name': 'reg2',
                'state': 'done',
            }
        ])
        self.assertEqual(self.event.seats_taken, 1)
        self.assertEqual(self.event_2.seats_taken, 1)
        self.ticket.write({
            'seats_max': 2,
            'seats_limited': True,
        })
        self.ticket_2.write({
            'seats_max': 2,
            'seats_limited': True,
        })
        self.env['event.registration'].create([
            {'event_id': e.id, 'sale_order_id': self.so.id, 'partner_id': p.id, 'event_ticket_id': t.id}
            for p in [(self.partner), (self.partner_admin)]
            for e, t in [(self.event, self.ticket), (self.event_2, self.ticket_2)]
        ])
        route_kwargs = {
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method.id,
            'token_id': None,
            'amount': self.so.amount_total,
            'flow': 'direct',
            'tokenization_requested': False,
            'landing_route': '/shop/payment/validate',
            'is_validation': False,
            'csrf_token': odoo.http.Request.csrf_token(self),
            'access_token': self.so._portal_ensure_token(),
        }
        with self.assertRaisesRegex(odoo.tests.JsonRpcException, 'odoo.exceptions.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)
