# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Command
from odoo.tests import Form, HttpCase, tagged

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
        self.ticket.write({'seats_max': 1, 'seats_limited': True})
        self.partner.write(self.dummy_partner_address_values.copy())

        so1 = self._create_so(
            order_line=[
                Command.create({
                    'product_id': self.ticket.product_id.id,
                    'event_id': self.event.id,
                    'event_ticket_id': self.ticket.id,
                })
            ]
        )
        so2 = self._create_so(
            order_line=[
                Command.create({
                    'product_id': self.ticket.product_id.id,
                    'event_id': self.event.id,
                    'event_ticket_id': self.ticket.id,
                })
            ]
        )

        # Create registrations
        editor = Form(self.env['registration.editor'].with_context(default_sale_order_id=so1.id))
        editor.save().action_make_registration()
        editor = Form(self.env['registration.editor'].with_context(default_sale_order_id=so2.id))
        editor.save().action_make_registration()

        # SO2 is confirmed first
        so2.action_confirm()

        self.env.flush_all()  # Command-created records won't trigger a recompute until flush
        self.assertEqual(self.event.seats_available, 0)
        self.assertEqual(self.event.seats_taken, 1)

        # SO1 tries to checkout
        website = self.website.with_user(self.public_user)
        with MockRequest(website.env, website=website, path='/shop/checkout', sale_order_id=so1.id):
            response = self.CheckoutController.shop_checkout()

        # SO2 was too quick and confirmed before SO1 => SO1 is redirected to change tickets
        self.assertEqual(response.status_code, 303, 'SEE OTHER')
        self.assertURLEqual(response.location, '/shop/cart')
        self.assertIn("There are not enough seats available", so1._join_alert_messages())
