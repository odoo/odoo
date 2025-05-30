# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import HttpCase, tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.website_sale.controllers.main import WebsiteSale as CheckoutController
from odoo.addons.website_sale.tests.common import MockRequest


@tagged('post_install', '-at_install')
class TestEventCheckout(TestWebsiteEventSaleCommon, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.CheckoutController = CheckoutController()

    def test_checkout_impossible_if_tickets_are_expired(self):
        self.ticket.write({
            'seats_max': 1,
            'seats_limited': True,
        })

        so1 = self._create_so(order_line=[Command.create({
            'product_id': self.ticket.product_id.id,
            'event_id': self.event.id,
            'event_ticket_id': self.ticket.id,
        })])
        so2 = self._create_so(order_line=[Command.create({
            'product_id': self.ticket.product_id.id,
            'event_id': self.event.id,
            'event_ticket_id': self.ticket.id,
        })])
        self.env['event.registration'].create([
            {
                'state': 'draft',
                'sale_order_id': so1.id,
                'partner_id': so1.partner_id.id,
                'event_id': self.event.id,
                'event_ticket_id': self.ticket.id,
            },
        ])

        so2.action_confirm()
        self.assertEqual(self.event.seats_available, 0)
        self.assertEqual(self.event.seats_taken, 1)

        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website, path='/shop/checkout', sale_order_id=so1.id):
            response = self.CheckoutController.shop_checkout()

        # SO2 was too quick and registered before SO1 => redirected to change tickets
        self.assertEqual(response.status_code, 303, 'SEE OTHER')
        self.assertURLEqual(response.location, '/shop/cart')
