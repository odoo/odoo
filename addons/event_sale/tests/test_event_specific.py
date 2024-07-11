# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from dateutil.relativedelta import relativedelta

from odoo.addons.event_sale.tests.common import TestEventSaleCommon
from odoo.tests.common import Form


class TestEventSpecific(TestEventSaleCommon):

    def test_event_change_max_seat_no_side_effect(self):
        """
        Test that changing the Maximum (seats_max), the seats_reserved of all the ticket do not change
        """
        # Enable "sell tickets with sales orders" so that we have a price column on the tickets
        # Event template
        with Form(self.env['event.type']) as event_type_form:
            event_type_form.name = "Pastafarian Event Template"
            # Edit the default line
            with event_type_form.event_type_ticket_ids.new() as ticket_line:
                ticket_line.name = 'Pastafarian Registration'
                ticket_line.price = 0
            event_type = event_type_form.save()

        with Form(self.env['event.event']) as event_event_form:
            event_event_form.name = 'Annual Pastafarian Reunion (APR)'
            event_event_form.date_begin = datetime.datetime.now() + relativedelta(days=2)
            event_event_form.date_end = datetime.datetime.now() + relativedelta(days=3)
            event_event_form.event_type_id = event_type  # Set the template
            # Create second ticket (VIP)
            with event_event_form.event_ticket_ids.new() as ticket_line:
                ticket_line.name = 'VIP (Very Important Pastafarian)'
                ticket_line.price = 10
            event_event = event_event_form.save()

        # Add two registrations for the event, one registration for each ticket type
        for ticket in event_event.event_ticket_ids:
            self.env['event.registration'].create({
                'event_id': event_event.id,
                'event_ticket_id': ticket.id
            })

        # Edit the maximum
        before_confirmed = [t.seats_reserved for t in event_event.event_ticket_ids]
        with Form(event_event) as event_event_form:
            with event_event_form.event_ticket_ids.edit(0) as ticket_line:
                ticket_line.seats_max = ticket_line.seats_max + 1
        after_confirmed = [t.seats_reserved for t in event_event.event_ticket_ids]
        self.assertEqual(before_confirmed, after_confirmed)
