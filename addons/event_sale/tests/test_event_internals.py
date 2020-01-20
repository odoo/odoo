# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.addons.event_sale.tests.common import TestEventSaleCommon
from odoo.fields import Datetime as FieldsDatetime
from odoo.tests.common import users


class EventSaleTest(TestEventSaleCommon):

    @users('user_eventmanager')
    def test_event_configuration_from_type(self):
        """ In addition to event test, also test tickets configuration coming
        from event_sale capabilities. """
        event_type = self.event_type_complex.with_user(self.env.user)
        event_type.write({
            'use_mail_schedule': False,
            'use_ticketing': False,
        })
        # Event type does not use tickets but data is kept for compatibility and avoid recreating them
        self.assertEqual(len(event_type.event_ticket_ids), 1)
        self.assertEqual(event_type.event_ticket_ids.name, 'Registration')

        event = self.env['event.event'].create({
            'name': 'Event Update Type',
            'event_type_id': event_type.id,
            'date_begin': FieldsDatetime.to_string(datetime.today() + timedelta(days=1)),
            'date_end': FieldsDatetime.to_string(datetime.today() + timedelta(days=15)),
        })
        event._onchange_type()
        self.assertEqual(event.event_ticket_ids, self.env['event.event.ticket'])

        event_type.write({
            'use_ticketing': True,
            'event_ticket_ids': [(5, 0), (0, 0, {
                'name': 'First Ticket',
                'product_id': self.event_product.id,
            })]
        })
        event_type.event_ticket_ids._onchange_product_id()
        event._onchange_type()
        self.assertEqual(event.event_ticket_ids.name, 'Registration for %s' % event.name)
        self.assertEqual(event.event_ticket_ids.product_id, self.event_product)
        self.assertEqual(event.event_ticket_ids.price, self.event_product.list_price)

    def test_event_registrable(self):
        """Test if `_compute_event_registrations_open` works properly."""
        test_event = self.env['event.event'].create({
            'name': 'TestEvent',
            'date_begin': datetime.now() - timedelta(days=5),
            'date_end': datetime.now() + timedelta(days=5),
        })
        test_event_ticket = self.env['event.event.ticket'].create({
            'name': 'TestTicket',
            'event_id': test_event.id,
            'product_id': self.env['product.product'].search([], limit=1).id,
        })

        self.assertEqual(test_event.event_registrations_open, True)

        test_event.write({
            'date_begin': datetime.now() - timedelta(days=5),
            'date_end': datetime.now() - timedelta(days=1),
        })

        test_event.date_end = datetime.now() - timedelta(days=1)
        self.assertEqual(test_event.event_registrations_open, False)

        test_event.write({
            'date_begin': datetime.now() - timedelta(days=1),
            'date_end': datetime.now() + timedelta(days=5),
        })

        test_event.write({'event_ticket_ids': [(5, 0)]})
        self.assertEqual(test_event.event_registrations_open, False, 'cannot register if no tickets')

        test_event_ticket = self.env['event.event.ticket'].create({
            'name': 'TestTicket',
            'event_id': test_event.id,
            'product_id': self.env['product.product'].search([], limit=1).id,
        })
        test_event_ticket.product_id.active = False
        self.assertEqual(test_event.event_registrations_open, False, 'cannot register if product linked to the tickets are all archived')
