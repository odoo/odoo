# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
from unittest.mock import patch

from odoo.addons.event_sale.tests.common import TestEventSaleCommon
from odoo.fields import Datetime as FieldsDatetime, Date as FieldsDate
from odoo.tests.common import users


class TestEventData(TestEventSaleCommon):

    @users('user_eventmanager')
    def test_event_configuration_from_type(self):
        """ In addition to event test, also test tickets configuration coming
        from event_sale capabilities. """
        event_type = self.event_type_complex.with_user(self.env.user)
        event_type.write({
            'use_mail_schedule': False,
            'use_ticket': False,
        })
        self.assertEqual(event_type.event_type_ticket_ids, self.env['event.type.ticket'])

        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'event_type_id': event_type.id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })
        self.assertEqual(event.event_ticket_ids, self.env['event.event.ticket'])

        event_type.write({
            'use_ticket': True,
            'event_type_ticket_ids': [(5, 0), (0, 0, {
                'name': 'First Ticket',
                'product_id': self.event_product.id,
                'seats_max': 5,
            })]
        })
        self.assertEqual(event_type.event_type_ticket_ids.description, self.event_product.description_sale)

        # synchronize event
        event.write({'event_type_id': event_type.id})
        self.assertEqual(event.event_ticket_ids.name, event.event_type_id.event_type_ticket_ids.name)
        self.assertTrue(event.event_ticket_ids.seats_limited)
        self.assertEqual(event.event_ticket_ids.seats_max, 5)
        self.assertEqual(event.event_ticket_ids.product_id, self.event_product)
        self.assertEqual(event.event_ticket_ids.price, self.event_product.list_price)
        self.assertEqual(event.event_ticket_ids.description, self.event_product.description_sale)

    def test_event_registrable(self):
        """Test if `_compute_event_registrations_open` works properly with additional
        product active conditions compared to base tests (see event) """
        event = self.event_0.with_user(self.env.user)
        self.assertTrue(event.event_registrations_open)

        # ticket without dates boundaries -> ok
        ticket = self.env['event.event.ticket'].create({
            'name': 'TestTicket',
            'event_id': event.id,
            'product_id': self.event_product.id,
        })
        self.assertTrue(event.event_registrations_open)

        # ticket has inactive product -> ko
        ticket.product_id.action_archive()
        self.assertFalse(event.event_registrations_open)

        # at least one valid ticket -> ok is back
        event_product = self.env['product.product'].create({'name': 'Test Registration Product New',})
        new_ticket = self.env['event.event.ticket'].create({
            'name': 'TestTicket 2',
            'event_id': event.id,
            'product_id': event_product.id,
            'end_sale_date': datetime.now() + timedelta(days=2),
        })
        self.assertTrue(new_ticket.sale_available)
        self.assertTrue(event.event_registrations_open)


class TestEventTicketData(TestEventSaleCommon):

    def setUp(self):
        super(TestEventTicketData, self).setUp()
        self.ticket_date_patcher = patch('odoo.addons.event.models.event_ticket.fields.Date', wraps=FieldsDate)
        self.ticket_date_patcher_mock = self.ticket_date_patcher.start()
        self.ticket_date_patcher_mock.context_today.return_value = date(2020, 1, 31)

    def tearDown(self):
        super(TestEventTicketData, self).tearDown()
        self.ticket_date_patcher.stop()

    @users('user_eventmanager')
    def test_event_ticket_fields(self):
        """ Test event ticket fields synchronization """
        event = self.event_0.with_user(self.env.user)
        event.write({
            'event_ticket_ids': [
                (5, 0),
                (0, 0, {
                    'name': 'First Ticket',
                    'product_id': self.event_product.id,
                    'seats_max': 30,
                }), (0, 0, {  # limited in time, available (01/10 (start) < 01/31 (today) < 02/10 (end))
                    'name': 'Second Ticket',
                    'product_id': self.event_product.id,
                    'start_sale_date': date(2020, 1, 10),
                    'end_sale_date': date(2020, 2, 10),
                })
            ],
        })
        first_ticket = event.event_ticket_ids.filtered(lambda t: t.name == 'First Ticket')
        second_ticket = event.event_ticket_ids.filtered(lambda t: t.name == 'Second Ticket')
        # force second ticket price, after calling the onchange
        second_ticket.write({'price': 8.0})

        # price coming from product
        self.assertEqual(first_ticket.price, self.event_product.list_price)
        self.assertEqual(second_ticket.price, 8.0)

        # default availability
        self.assertTrue(first_ticket.seats_limited)
        self.assertTrue(first_ticket.sale_available)
        self.assertFalse(first_ticket.is_expired)
        self.assertFalse(second_ticket.seats_limited)
        self.assertTrue(second_ticket.sale_available)
        self.assertFalse(second_ticket.is_expired)

        # product archived
        self.event_product.action_archive()
        self.assertFalse(first_ticket.sale_available)
        self.assertFalse(second_ticket.sale_available)

        # sale is ended
        self.event_product.action_unarchive()
        second_ticket.write({'end_sale_date': date(2020, 1, 20)})
        self.assertFalse(second_ticket.sale_available)
        self.assertTrue(second_ticket.is_expired)
        # sale has not started
        second_ticket.write({
            'start_sale_date': date(2020, 2, 10),
            'end_sale_date': date(2020, 2, 20),
        })
        self.assertFalse(second_ticket.sale_available)
        self.assertFalse(second_ticket.is_expired)
