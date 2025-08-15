from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.website_sale.tests.test_website_sale_cart_abandoned import (
    TestWebsiteSaleCartAbandonedCommon,
)


@tagged('post_install', '-at_install')
class TestWebsiteEventSaleCart(TestWebsiteEventSaleCommon, TestWebsiteSaleCartAbandonedCommon):
    def test_sold_out_event_cart_reminder(self):
        """Check that abandoned cart emails aren't sent for sold out tickets."""
        cart1, cart2 = carts = self.so1before + self.so2before
        carts.order_line.unlink()
        carts.website_id.send_abandoned_cart_email = True

        self.ticket.write({
            'seats_limited': True,
            'seats_max': 1,
        })

        create_order_line = [Command.create({
            'product_id': self.product_event.id,
            'event_id': self.event.id,
            'event_ticket_id': self.ticket.id,
        })]
        cart1.order_line = create_order_line
        cart2.order_line = create_order_line
        self.assertTrue(
            self.send_mail_patched(cart1.id),
            "Abandoned cart email should be sent for availlable tickets",
        )

        # Create registrations & confirm first order
        editor = self.env['registration.editor'].new()
        editor.with_context(default_sale_order_id=cart1.id).action_make_registration()
        cart1.action_confirm()
        self.assertEqual(self.ticket.seats_available, 0)
        self.assertFalse(
            self.send_mail_patched(cart2.id),
            "Abandoned cart email should not be sent when ticket has no seats available",
        )

        # Reset sent state, increase seat limit, and try again
        cart2.cart_recovery_email_sent = False
        self.ticket.seats_max = 2
        self.assertTrue(
            self.send_mail_patched(cart2.id),
            "Abandoned cart email can be sent after increasing seat count",
        )
