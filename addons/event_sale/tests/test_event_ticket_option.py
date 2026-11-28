# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import Command
from odoo.tests import Form, tagged

from odoo.addons.event_sale.tests.common import TestEventSaleCommon


@tagged('event_flow', 'at_install', '-post_install')
class TestEventTicketOption(TestEventSaleCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.lunch, cls.party, cls.other = cls.env['product.product'].create([
            {'name': 'Lunch', 'list_price': 20, 'type': 'service'},
            {'name': 'Party', 'list_price': 35, 'type': 'service'},
            {'name': 'Other', 'list_price': 5, 'type': 'service'},
        ])
        cls.ticket, cls.ticket_no_option = cls.env['event.event.ticket'].create([{
            'name': 'With options',
            'event_id': cls.event_0.id,
            'product_id': cls.event_product.id,
            'price': 10,
            'optional_product_ids': [Command.set((cls.lunch | cls.party).ids)],
        }, {
            'name': 'Without options',
            'event_id': cls.event_0.id,
            'product_id': cls.event_product.id,
            'price': 10,
        }])

    def _make_order(self, quantity=3, options=None):
        """ Quotation with a ticket line and, optionally, option lines
        ``{product: quantity}`` as the event configurator creates them. """
        order = self.env['sale.order'].create({
            'partner_id': self.event_customer.id,
            'order_line': [Command.create({
                'product_id': self.event_product.id,
                'event_id': self.event_0.id,
                'event_ticket_id': self.ticket.id,
                'product_uom_qty': quantity,
                'price_unit': 10,
            })],
        })
        ticket_line = order.order_line
        for product, option_quantity in (options or {}).items():
            order.order_line = [Command.create({
                'product_id': product.id,
                'product_uom_qty': option_quantity,
                'linked_line_id': ticket_line.id,
                'is_event_ticket_option': True,
            })]
        return order

    def _confirm(self, order):
        order.action_confirm()
        return order.order_line.registration_ids.sorted('id')

    def _option_lines(self, order):
        return {
            line.product_id: line.product_uom_qty
            for line in order.order_line.filtered('is_event_ticket_option')
            if line.product_uom_qty
        }

    def test_no_option_selected_by_default(self):
        order = self._make_order()
        registrations = self._confirm(order)
        self.assertEqual(len(registrations), 3)
        self.assertFalse(registrations.ticket_option_product_ids)
        self.assertFalse(self._option_lines(order))

    def test_registration_options_update_order(self):
        order = self._make_order()
        alice, bob, carl = self._confirm(order)
        ticket_line = order.order_line.filtered('event_ticket_id')

        alice.ticket_option_product_ids = self.lunch
        self.assertEqual(self._option_lines(order), {self.lunch: 1}, 'created on the first tick')
        self.assertEqual(order.order_line.filtered('is_event_ticket_option').linked_line_id, ticket_line)

        (bob | carl).ticket_option_product_ids = self.lunch | self.party
        self.assertEqual(self._option_lines(order), {self.lunch: 3, self.party: 2})

        bob.ticket_option_product_ids = self.party
        self.assertEqual(self._option_lines(order), {self.lunch: 2, self.party: 2})

        carl.action_cancel()
        self.assertEqual(self._option_lines(order), {self.lunch: 1, self.party: 1})

        (alice | bob).ticket_option_product_ids = False
        self.assertFalse(self._option_lines(order), 'an option nobody has is at zero')

    def test_registrations_created_with_options(self):
        order = self._make_order(quantity=1)
        self._confirm(order)
        ticket_line = order.order_line.filtered('event_ticket_id')
        self.env['event.registration'].create([{
            'event_id': self.event_0.id,
            'name': 'Dave',
            'sale_order_line_id': ticket_line.id,
            'ticket_option_product_ids': [Command.set(self.party.ids)],
        }, {
            'event_id': self.event_0.id,
            'name': 'Eve',
            'sale_order_line_id': ticket_line.id,
            'ticket_option_product_ids': [Command.set(self.party.ids)],
        }])
        self.assertEqual(self._option_lines(order), {self.party: 2})

    def test_ticket_change_drops_options(self):
        order = self._make_order(quantity=1)
        registration = self._confirm(order)
        registration.ticket_option_product_ids = self.lunch
        with Form(registration) as form:
            form.event_ticket_id = self.ticket_no_option
        self.assertFalse(form.ticket_option_product_ids)

    def test_options_of_order_seed_attendees(self):
        order = self._make_order(options={self.lunch: 2, self.party: 3, self.other: 3})
        registrations = self._confirm(order)
        self.assertEqual(len(registrations), 3)
        self.assertEqual(registrations[0].ticket_option_product_ids, self.lunch | self.party)
        self.assertEqual(registrations[1].ticket_option_product_ids, self.lunch | self.party)
        self.assertEqual(registrations[2].ticket_option_product_ids, self.party)
        self.assertEqual(
            self._option_lines(order), {self.lunch: 2, self.party: 3},
            'products that are not options of the ticket are dropped')

    def test_registration_editor_options(self):
        order = self._make_order(options={self.lunch: 3})
        order.action_confirm()
        editor = self.env['registration.editor'].with_context(default_sale_order_id=order.id).create({})
        lines = editor.event_registration_ids
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines.ticket_option_product_ids, self.lunch, 'seeded from the order')

        lines[0].ticket_option_product_ids = False
        lines[1].ticket_option_product_ids = self.lunch | self.party
        editor.action_make_registration()
        self.assertEqual(self._option_lines(order), {self.lunch: 2, self.party: 1})

    def test_locked_order_only_notifies(self):
        order = self._make_order(options={self.lunch: 1})
        registration = self._confirm(order)[0]
        self.assertEqual(registration.ticket_option_product_ids, self.lunch)
        order.locked = True
        activities = self.env['mail.activity'].search([('res_id', '=', order.id), ('res_model', '=', 'sale.order')])

        registration.ticket_option_product_ids = self.lunch | self.party
        self.assertEqual(self._option_lines(order), {self.lunch: 1}, 'a locked order is not edited')
        new_activities = self.env['mail.activity'].search([
            ('res_id', '=', order.id), ('res_model', '=', 'sale.order'),
        ]) - activities
        self.assertEqual(len(new_activities), 1)
