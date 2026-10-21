# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta

from odoo.addons.event.tests.common import EventCase
from odoo.tests import tagged


class TestDisplayNameCommon(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.reference_beg = datetime(2025, 4, 21, 6, 30, 0)
        cls.reference_end = datetime(2025, 8, 21, 17, 45, 0)

        # A limited event with 5 seats and 2 tickets (limited + unlimited)
        cls.limited_event = cls.env['event.event'].create({
            'name': 'Summer Workshop',
            'date_begin': cls.reference_beg,
            'date_end': cls.reference_end,
            'seats_limited': True,
            'seats_max': 5,
            'event_ticket_ids': [
                (0, 0, {
                    'name': 'Standard',
                    'seats_limited': True,
                    'seats_max': 3,
                }),
                (0, 0, {
                    'name': 'VIP',
                    'seats_limited': False,
                }),
            ],
        })
        cls.ticket_standard = cls.limited_event.event_ticket_ids.filtered(
            lambda t: t.name == 'Standard'
        )
        cls.ticket_vip = cls.limited_event.event_ticket_ids.filtered(
            lambda t: t.name == 'VIP'
        )

        # A multi-slot event used to verify that ticket display name is suppressed
        cls.multi_slot_event = cls.env['event.event'].create({
            'name': 'Multi Slot Conference',
            'date_begin': cls.reference_beg,
            'date_end': cls.reference_end + timedelta(days=5),
            'is_multi_slots': True,
            'event_slot_ids': [
                (0, 0, {
                    'date': date(2025, 6, 1),
                    'start_hour': 9,
                    'end_hour': 12,
                }),
                (0, 0, {
                    'date': date(2025, 6, 2),
                    'start_hour': 14,
                    'end_hour': 17,
                }),
            ],
            'event_ticket_ids': [
                (0, 0, {
                    'name': 'Slot Ticket',
                    'seats_limited': True,
                    'seats_max': 10,
                }),
            ],
        })
        cls.ticket_slot = cls.multi_slot_event.event_ticket_ids[0]


@tagged('event_event', 'at_install', '-post_install')
class TestEventDisplayName(TestDisplayNameCommon):
    """Tests for event.event._compute_display_name."""

    def test_event_display_name_seats_availability(self):
        """Display name includes seat availability when requested."""
        event = self.limited_event

        # Without the context, only the event name is displayed.
        self.assertEqual(event.display_name, 'Summer Workshop')

        # No registrations: 5 seats remaining.
        # With name_with_seats_availability, a limited event shows remaining seats.
        self.assertEqual(
            event.with_context(name_with_seats_availability=True).display_name,
            'Summer Workshop (5 seats remaining)',
        )

        # 1 registration: 4 seats remaining.
        self._create_registrations(event, 1)
        # With formatted_display_name, availability is wrapped with '--' markers.
        self.assertEqual(
            event.with_context(
                name_with_seats_availability=True,
                formatted_display_name=True,
            ).display_name,
            'Summer Workshop --(4 seats remaining)--',
        )

        # 4 additional registrations: event is sold out.
        self._create_registrations(event, 4)
        self.assertEqual(
            event.with_context(name_with_seats_availability=True).display_name,
            'Summer Workshop (Sold out)',
        )
        self.assertEqual(
            event.with_context(
                name_with_seats_availability=True,
                formatted_display_name=True,
            ).display_name,
            'Summer Workshop --(Sold out)--',
        )

    def test_event_display_name_unlimited_no_suffix(self):
        """An unlimited event (no seats_max) shows no availability suffix."""
        unlimited_event = self.env['event.event'].create({
            'name': 'Open Event',
            'date_begin': self.reference_beg,
            'date_end': self.reference_end,
            'seats_limited': False,
        })
        self.assertEqual(
            unlimited_event.with_context(name_with_seats_availability=True).display_name,
            'Open Event',
        )


@tagged('event_ticket', 'at_install', '-post_install')
class TestEventTicketDisplayName(TestDisplayNameCommon):
    """Tests for event.event.ticket._compute_display_name."""

    def test_ticket_display_name_seats_availability(self):
        """Display name includes ticket seat availability when requested."""
        ticket = self.ticket_standard
        event = self.limited_event

        # Without the availability context, only the ticket name is displayed.
        self.assertEqual(ticket.display_name, 'Standard')

        # No registrations: 3 seats remaining.
        # With name_with_seats_availability, a limited ticket shows remaining seats.
        self.assertEqual(
            ticket.with_context(name_with_seats_availability=True).display_name,
            'Standard (3 seats remaining)',
        )

        # 1 registration: 2 seats remaining.
        self._create_registrations_for_slot_and_ticket(event, False, ticket, 1)
        # With formatted_display_name, ticket availability is wrapped with '--' markers.
        self.assertEqual(
            ticket.with_context(
                name_with_seats_availability=True,
                formatted_display_name=True,
            ).display_name,
            'Standard --(2 seats remaining)--',
        )

        # 2 additional registrations: the ticket is sold out.
        self._create_registrations_for_slot_and_ticket(event, False, ticket, 2)
        self.assertEqual(
            ticket.with_context(name_with_seats_availability=True).display_name,
            'Standard (Sold out)',
        )
        self.assertEqual(
            ticket.with_context(
                name_with_seats_availability=True,
                formatted_display_name=True,
            ).display_name,
            'Standard --(Sold out)--',
        )

    def test_ticket_display_name_multi_slot_suppressed(self):
        """Ticket on a multi-slot event must not show availability suffix."""
        ticket = self.ticket_slot
        # Even with availability context, multi-slot events suppress the suffix
        self.assertEqual(
            ticket.with_context(name_with_seats_availability=True).display_name,
            'Slot Ticket',
        )

    def test_ticket_display_name_unlimited_no_suffix(self):
        """An unlimited ticket (seats_max=0) shows no availability suffix."""
        ticket = self.ticket_vip
        self.assertEqual(
            ticket.with_context(name_with_seats_availability=True).display_name,
            'VIP',
        )
