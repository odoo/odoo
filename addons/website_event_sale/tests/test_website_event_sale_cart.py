from datetime import datetime, timedelta

from odoo import Command
from odoo.tests import tagged, Form

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon
from odoo.addons.website_sale.tests.test_website_sale_cart_abandoned import (
    TestWebsiteSaleCartAbandonedCommon,
)


@tagged('post_install', '-at_install')
class TestWebsiteEventSaleCart(TestWebsiteEventSaleCommon, TestWebsiteSaleCartAbandonedCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.website.write({
            'send_abandoned_cart_email': True,
            'cart_abandoned_delay': 1.0,  # 1 hour
        })
        cls.website.send_abandoned_cart_email_activation_time -= timedelta(weeks=1)

        cls.partner_admin = cls.env.ref('base.partner_admin')
        if not cls.partner_admin.email:
            cls.partner_admin.email = 'base@partner.admin'

    def test_sold_out_event_cart_reminder(self):
        """Check that abandoned cart emails aren't sent for sold out tickets."""
        cart1, cart2 = self.env['sale.order'].create([{
            'partner_id': partner.id,
            'website_id': self.website.id,
            'date_order': datetime.now() - timedelta(hours=2),
        } for partner in (self.partner_admin, self.partner_portal)])

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
        editor = Form(self.env['registration.editor'].with_context(default_sale_order_id=cart1.id))
        editor.save().action_make_registration()
        cart1.action_confirm()
        # command-created records won't trigger a recompute until flush
        self.env.flush_all()
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
