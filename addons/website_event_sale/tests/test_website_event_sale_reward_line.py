# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import tagged

from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged('post_install', '-at_install')
class TestWebsiteEventSaleRewardLine(TestWebsiteEventSaleCommon):
    """ A reward line (coupon, gift card, eWallet, ...) bringing an unconfirmed
    website cart (sale order) to zero must not confirm its registrations before checkout.
    If there is ever a need for a website_event_sale_loyalty module, this class
    could just be ported there. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.reward_product = cls.env['product.product'].create({
            'name': 'Reward (simulated gift card)',
            'type': 'service',
            'taxes_id': [Command.set(cls.zero_tax.ids)],
        })
        cls.cart = cls.env['sale.order'].create({
            'partner_id': cls.partner.id,
            'website_id': cls.website.id,
            'order_line': [Command.create({
                'product_id': cls.product_event.id,
                'event_id': cls.event.id,
                'event_ticket_id': cls.ticket.id,
            })],
        })

    def _create_registration(self):
        return self.env['event.registration'].create({
            'event_id': self.event.id,
            'event_ticket_id': self.ticket.id,
            'sale_order_id': self.cart.id,
            'sale_order_line_id': self.cart.order_line.id,
            'name': 'Test Attendee',
            'email': 'attendee@example.com',
        })

    def _apply_reward_line_full_amount(self):
        # Simulate a gift card which is a separate negative order line covering the cart
        self.cart.order_line = [Command.create({
            'product_id': self.reward_product.id,
            'price_unit': -self.cart.amount_total,
        })]
        # run pending recomputes and their side effects, like mail
        self.env.flush_all()
        # safety check
        self.assertTrue(self.cart.currency_id.is_zero(self.cart.amount_total))

    def test_registration_state_not_changed_until_checkout(self):
        registration = self._create_registration()
        self.assertEqual((registration.state, registration.sale_status), ('draft', 'to_pay'))

        self._apply_reward_line_full_amount()
        self.assertEqual((registration.state, registration.sale_status), ('draft', 'to_pay'))

        # a zero amount checkout eventually leads to action_confirm
        self.cart.action_confirm()
        self.assertEqual((registration.state, registration.sale_status), ('open', 'sold'))

    def test_confirmation_mail_not_sent_until_checkout(self):
        registration = self._create_registration()
        self._apply_reward_line_full_amount()
        self.assertFalse(registration.mail_registration_ids.filtered('mail_sent'))

        self.cart.action_confirm()
        self.assertTrue(registration.mail_registration_ids.filtered('mail_sent'))

    def test_event_not_sold_out_until_checkout(self):
        self.event.write({
            'seats_limited': True,
            'seats_max': 1,
        })
        self._create_registration()
        self._apply_reward_line_full_amount()
        self.assertFalse(self.event.event_registrations_sold_out)

        self.cart.action_confirm()
        self.assertTrue(self.event.event_registrations_sold_out)
