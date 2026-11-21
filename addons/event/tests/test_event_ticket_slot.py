from datetime import date, datetime

from odoo.addons.event.tests.common import EventCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('event_slot', 'event_ticket')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestEventTicketSlot(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['event.event'].create({
            'name': 'Two Days Festival',
            'date_begin': datetime(2025, 6, 10, 0, 0, 0),
            'date_end': datetime(2025, 6, 11, 23, 59, 59),
            'date_tz': 'UTC',
            'is_multi_slots': True,
            'event_slot_ids': [
                (0, 0, {'date': date(2025, 6, 10), 'start_hour': 9, 'end_hour': 18}),
                (0, 0, {'date': date(2025, 6, 11), 'start_hour': 9, 'end_hour': 18}),
            ],
            'event_ticket_ids': [
                (0, 0, {'name': 'Full Access'}),
                (0, 0, {'name': 'Day One Pass'}),
            ],
        })
        cls.slot_1, cls.slot_2 = cls.event.event_slot_ids.sorted('date')
        cls.ticket_all = cls.event.event_ticket_ids.filtered(lambda t: t.name == 'Full Access')
        cls.ticket_day_1 = cls.event.event_ticket_ids - cls.ticket_all
        cls.ticket_day_1.event_slot_ids = cls.slot_1

    def _register(self, slot, ticket):
        return self.env['event.registration'].create({
            'event_id': self.event.id,
            'event_slot_id': slot.id,
            'event_ticket_id': ticket.id,
            'name': 'Attendee',
        })

    def test_availability(self):
        availability = self.event._get_seats_availability([
            (self.slot_1, self.ticket_all), (self.slot_2, self.ticket_all),
            (self.slot_1, self.ticket_day_1), (self.slot_2, self.ticket_day_1),
        ])
        self.assertEqual(availability, [None, None, None, 0])

    def test_registration_constraint(self):
        self._register(self.slot_1, self.ticket_day_1)
        self._register(self.slot_2, self.ticket_all)
        with self.assertRaises(ValidationError):
            self._register(self.slot_2, self.ticket_day_1)
        # moving an existing attendee to a forbidden date is blocked too
        registration = self._register(self.slot_1, self.ticket_day_1)
        with self.assertRaises(ValidationError):
            registration.event_slot_id = self.slot_2

    def test_slot_without_valid_ticket_is_closed(self):
        self.ticket_all.unlink()
        self.assertEqual(
            self.event._get_seats_availability([
                (self.slot_1, self.ticket_day_1), (self.slot_2, self.ticket_day_1),
            ]),
            [None, 0],
            "The only ticket left is not valid on the second slot: no seat there")
        self.assertFalse(self.event.event_registrations_sold_out)

    def test_foreign_slot_refused(self):
        other_event = self.event.copy()
        with self.assertRaises(ValidationError):
            self.ticket_day_1.event_slot_ids = other_event.event_slot_ids[:1]
