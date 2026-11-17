# Part of Odoo. See LICENSE file for full copyright and licensing details.

import re

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.base.tests.common import HttpCaseWithUserPortal
from odoo.addons.website_event_sale.tests.common import TestWebsiteEventSaleCommon


@tagged('post_install', '-at_install')
class TestTicketOption(HttpCaseWithUserPortal, TestWebsiteEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lunch, cls.party, cls.not_an_option = cls.env['product.product'].create([
            {'name': 'Lunch', 'list_price': 20, 'type': 'service'},
            {'name': 'Party', 'list_price': 35, 'type': 'service'},
            {'name': 'Unrelated Product', 'list_price': 999, 'type': 'service'},
        ])
        cls.ticket.sudo().optional_product_ids = cls.lunch | cls.party
        questions = cls.event.question_ids
        cls.q_name = questions.filtered(lambda q: q.question_type == 'name')
        cls.q_email = questions.filtered(lambda q: q.question_type == 'email')

    def _attendee(self, index, name, ticket, options=()):
        data = {
            f'{index}-name-{self.q_name.id}': name,
            f'{index}-email-{self.q_email.id}': f'{name.lower()}@test.lan',
            f'{index}-event_ticket_id': ticket.id,
        }
        data.update({f'ticket_option_{index}_{option.id}': '1' for option in options})
        return data

    def _confirm(self, *attendees, **extra):
        data = {'csrf_token': self.csrf_token(), **extra}
        for attendee in attendees:
            data.update(attendee)
        before = self.event.registration_ids
        self.url_open(f'/event/{self.event.id}/registration/confirm', data=data)
        self.event.invalidate_recordset(['registration_ids'])
        return (self.event.registration_ids - before).sorted('id')

    def _option_lines(self, order):
        return {
            line.product_id: line.product_uom_qty
            for line in order.order_line.filtered('is_event_ticket_option')
        }

    def test_form_displays_options(self):
        self.authenticate(None, None)
        html = self.make_jsonrpc_request(
            f'/event/{self.event.id}/registration/new', {f'nb_register-{self.ticket.id}': '2'})
        for index in (1, 2):
            self.assertIn(f'name="ticket_option_{index}_{self.lunch.id}"', html)
            self.assertIn(f'name="ticket_option_{index}_{self.party.id}"', html)
        self.assertNotIn(f'ticket_option_3_{self.lunch.id}', html)
        self.assertIn('Lunch', html)
        option_inputs = re.findall(r'<input[^>]*name="ticket_option_[^>]*>', html)
        self.assertEqual(len(option_inputs), 4)
        self.assertFalse([tag for tag in option_inputs if 'checked' in tag], 'no option is preselected')

    def test_no_option_posted(self):
        self.authenticate(None, None)
        alice, bob = self._confirm(
            self._attendee(1, 'Alice', self.ticket),
            self._attendee(2, 'Bob', self.ticket),
        )
        self.assertFalse(alice.ticket_option_product_ids | bob.ticket_option_product_ids)
        self.assertFalse(self._option_lines(alice.sale_order_id))

    def test_options_added_to_cart(self):
        self.authenticate(None, None)
        alice, bob, carl = self._confirm(
            self._attendee(1, 'Alice', self.ticket, [self.lunch, self.party]),
            self._attendee(2, 'Bob', self.ticket, [self.lunch]),
            self._attendee(3, 'Carl', self.ticket),
        )
        self.assertEqual(alice.ticket_option_product_ids, self.lunch | self.party)
        self.assertEqual(bob.ticket_option_product_ids, self.lunch)
        self.assertFalse(carl.ticket_option_product_ids)

        order = alice.sale_order_id
        ticket_line = order.order_line.filtered('event_ticket_id')
        self.assertEqual(ticket_line.product_uom_qty, 3)
        self.assertEqual(self._option_lines(order), {self.lunch: 2, self.party: 1})
        option_lines = order.order_line.filtered('is_event_ticket_option')
        self.assertEqual(option_lines.linked_line_id, ticket_line)
        self.assertEqual(
            order.amount_untaxed,
            ticket_line.price_subtotal + 2 * 20 + 35,
        )

        # second booking in the same cart: same lines, quantities add up
        dave = self._confirm(self._attendee(1, 'Dave', self.ticket, [self.party]))
        self.assertEqual(dave.sale_order_id, order)
        self.assertEqual(self._option_lines(order), {self.lunch: 2, self.party: 2})

    def test_service_options_quick_checkout(self):
        """ Like tickets alone, tickets with service options go straight to the payment. """
        self.authenticate(None, None)
        alice = self._confirm(self._attendee(1, 'Alice', self.ticket, [self.lunch, self.party]))
        self.assertFalse(alice.sale_order_id._has_deliverable_products())
        self.assertFalse(alice.sale_order_id._needs_customer_address())
        response = self.url_open('/shop/checkout?try_skip_step=true')
        self.assertTrue(response.url.endswith('/shop/payment'))

    def test_goods_option_requires_delivery(self):
        self.authenticate(None, None)
        goodies = self.env['product.product'].create({'name': 'Goodies', 'list_price': 10, 'type': 'consu'})
        self.ticket.sudo().optional_product_ids |= goodies
        alice = self._confirm(self._attendee(1, 'Alice', self.ticket, [self.lunch, goodies]))
        self.assertEqual(self._option_lines(alice.sale_order_id), {self.lunch: 1, goodies: 1})
        self.assertTrue(alice.sale_order_id._has_deliverable_products())
        # the buyer created from the attendee has no street: the checkout asks for a delivery address
        response = self.url_open('/shop/checkout?try_skip_step=true')
        self.assertIn('address_type=delivery', response.url)

    def test_forged_options_are_ignored(self):
        self.authenticate(None, None)
        attendee = self._attendee(1, 'Eve', self.ticket, [self.not_an_option])
        attendee['1-ticket_option_product_ids'] = str(self.not_an_option.id)
        eve = self._confirm(attendee)
        self.assertEqual(len(eve), 1)
        self.assertFalse(eve.ticket_option_product_ids)
        self.assertFalse(eve.sale_order_id.order_line.filtered(lambda line: line.product_id == self.not_an_option))
        with self.assertRaises(ValidationError):
            eve.ticket_option_product_ids = self.not_an_option

    def test_free_ticket_with_paid_option(self):
        self.authenticate(None, None)
        free_ticket = self.env['event.event.ticket'].sudo().create({
            'event_id': self.event.id, 'name': 'Free', 'product_id': self.product_event.id, 'price': 0,
            'optional_product_ids': [(6, 0, self.lunch.ids)],
        })
        no_option = self._confirm(self._attendee(1, 'Fred', free_ticket))
        self.assertFalse(no_option.sale_order_id, 'Free ticket without option: no order, as in core')
        with_option = self._confirm(self._attendee(1, 'Gina', free_ticket, [self.lunch]))
        self.assertTrue(with_option.sale_order_id)
        self.assertEqual(self._option_lines(with_option.sale_order_id), {self.lunch: 1})
        self.assertEqual(with_option.sale_order_id.amount_untaxed, 20)

    def test_cart_updates(self):
        self.authenticate(None, None)
        alice, bob = self._confirm(
            self._attendee(1, 'Alice', self.ticket, [self.lunch]),
            self._attendee(2, 'Bob', self.ticket, [self.lunch, self.party]),
        )
        order = alice.sale_order_id
        ticket_line = order.order_line.filtered('event_ticket_id')
        lunch_line = order.order_line.filtered(lambda line: line.product_id == self.lunch)

        # customers cannot raise an option quantity by hand
        order._cart_update_line_quantity(line_id=lunch_line.id, quantity=5)
        self.assertEqual(lunch_line.product_uom_qty, 2)

        # lowering it removes the option from the last registered attendee
        order._cart_update_line_quantity(line_id=lunch_line.id, quantity=1)
        self.assertEqual(alice.ticket_option_product_ids, self.lunch)
        self.assertEqual(bob.ticket_option_product_ids, self.party)

        # removing one ticket cancels Bob: his party option leaves the cart
        order._cart_update_line_quantity(line_id=ticket_line.id, quantity=1)
        self.assertEqual(bob.state, 'cancel')
        self.assertEqual(self._option_lines(order), {self.lunch: 1})

        # removing the ticket line removes its options
        order._cart_update_line_quantity(line_id=ticket_line.id, quantity=0)
        self.assertFalse(order.order_line)
