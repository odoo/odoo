# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import odoo.tests
from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import JsonRpcException

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
        """Check that payments fails when there aren't enough seats available.
        - First check payment fails due to exceeding the ticket's limit
        - Then change to 2 unlimited tickets, which fails due to exceeding event limit
        - Finally do a successful purchase of a single ticket without limit
        """
        self.authenticate(None, None)
        self.ticket_2.write({
            'name': "VIP",
            'event_id': self.event.id,
            'seats_max': 1,
            'seats_limited': True,
        })
        self.event.write({
            'seats_max': 3,
            'seats_limited': True,
        })
        self.assertFalse(self.ticket.seats_limited)
        self.assertEqual(self.ticket_2.seats_available, 1)
        self.assertEqual(self.event.seats_available, 3)

        # Add VIP ticket to cart & create draft registration
        self.so.order_line = [Command.create({
            'product_id': self.ticket.product_id.id,
            'event_id': self.event.id,
            'event_ticket_id': self.ticket_2.id,
        })]
        registration = self.env['event.registration'].create({
            'state': 'draft',
            'partner_id': self.so.partner_id.id,
            'event_id': self.event.id,
            'event_ticket_id': self.ticket_2.id,
            'sale_order_id': self.so.id,
        })
        self.assertEqual(self.event.seats_taken, 0)
        self.assertEqual(self.event.event_ticket_ids.mapped('seats_taken'), [0, 0])

        # Sneaky Mitchell beats us to the punch
        self.event.registration_ids = [Command.create({
            'partner_id': self.partner_admin.id,
            'event_ticket_id': self.ticket_2.id,
            'state': 'done',
        })]
        self.assertEqual(self.event.seats_taken, 1)
        self.assertEqual(self.event.seats_available, 2)

        # Set up transaction values
        url = self._build_url(f'/shop/payment/transaction/{self.so.id}')
        route_kwargs = {
            'provider_id': self.provider.id,
            'payment_method_id': self.payment_method.id,
            'token_id': None,
            'flow': 'direct',
            'tokenization_requested': False,
            'landing_route': '/shop/payment/validate',
            'access_token': self.so._portal_ensure_token(),
        }

        # Payment should fail due to exceeding the VIP ticket limit
        with self.assertRaisesRegex(JsonRpcException, r'odoo\.exceptions\.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)
        # Double check that we hit the correct limit
        with self.assertRaises(ValidationError):
            self.ticket_2._check_seats_availability(minimal_availability=1)
        self.event._check_seats_availability(minimal_availability=1)

        # Replace VIP ticket with 2 regular tickets
        self.so.order_line.write({
            'product_id': self.ticket.product_id,
            'product_uom_qty': 2,
            'event_id': self.event.id,
            'event_ticket_id': self.ticket.id,
        })
        registration.event_ticket_id = self.ticket.id
        registration += registration.copy({'state': 'draft', 'sale_order_id': self.so.id})

        # Sneaky Mitchell beats us to the punch again
        self.event.registration_ids = [Command.create({
            'partner_id': self.partner_admin.id,
            'event_ticket_id': self.ticket.id,
            'state': 'done',
        })]
        self.assertEqual(self.event.seats_taken, 2)
        self.assertEqual(self.event.seats_available, 1)

        # Payment should fail due to exceeding the event seat limit
        with self.assertRaisesRegex(JsonRpcException, r'odoo\.exceptions\.ValidationError'):
            self.make_jsonrpc_request(url, route_kwargs)
        # Double check that we hit the correct limit
        with self.assertRaises(ValidationError):
            self.event._check_seats_availability(minimal_availability=2)
        self.ticket._check_seats_availability(minimal_availability=1)

        # Payment should succeed when buying only one ticket
        self.so.order_line.product_uom_qty = 1
        registration[1].unlink()
        self.make_jsonrpc_request(url, route_kwargs)
        registration.exists().write({'state': 'open'})
        self.assertEqual(self.ticket.seats_taken, 2)
        self.assertEqual(self.event.seats_taken, 3)
