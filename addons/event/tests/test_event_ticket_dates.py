from datetime import date, datetime

from odoo.addons.event.tests.common import EventCase
from odoo.exceptions import ValidationError
from odoo.tests import tagged


@tagged('event_ticket')
@tagged('at_install', '-post_install')  # LEGACY at_install
class TestEventTicketDates(EventCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # 3 days conference, with a masterclass held the 2 days before
        cls.event = cls.env['event.event'].create({
            'name': 'Conference',
            'date_begin': datetime(2025, 6, 10, 8, 0, 0),
            'date_end': datetime(2025, 6, 12, 18, 0, 0),
            'date_tz': 'UTC',
            'event_ticket_ids': [
                (0, 0, {'name': 'Conference Pass'}),
                (0, 0, {
                    'name': 'MasterClass',
                    'date_begin': datetime(2025, 6, 8, 9, 0, 0),
                    'date_end': datetime(2025, 6, 9, 17, 0, 0),
                }),
                (0, 0, {
                    'name': 'Day 2 Pass',
                    'date_begin': datetime(2025, 6, 11, 8, 0, 0),
                    'date_end': datetime(2025, 6, 11, 18, 0, 0),
                }),
            ],
        })
        cls.ticket_pass, cls.ticket_master, cls.ticket_day_2 = cls.event.event_ticket_ids.sorted('id')

    def _register(self, ticket, **values):
        return self.env['event.registration'].create({
            'event_id': self.event.id,
            'event_ticket_id': ticket.id,
            'name': 'Attendee',
            **values,
        })

    def test_registration_dates(self):
        reg_pass, reg_master, reg_day_2 = (
            self._register(ticket) for ticket in (self.ticket_pass, self.ticket_master, self.ticket_day_2)
        )
        self.assertEqual(
            (reg_pass.event_begin_date, reg_pass.event_end_date),
            (self.event.date_begin, self.event.date_end),
            "A ticket without dates keeps the event dates")
        self.assertEqual(
            (reg_master.event_begin_date, reg_master.event_end_date),
            (datetime(2025, 6, 8, 9, 0, 0), datetime(2025, 6, 9, 17, 0, 0)),
            "A ticket may be valid outside the event dates")
        self.assertFalse(reg_master.is_one_day)
        self.assertEqual(
            (reg_day_2.event_begin_date, reg_day_2.event_end_date),
            (datetime(2025, 6, 11, 8, 0, 0), datetime(2025, 6, 11, 18, 0, 0)))
        self.assertTrue(reg_day_2.is_one_day, "A day pass is a one day registration on a multi-day event")

        # only one bound: the other one comes from the event
        self.ticket_pass.date_end = datetime(2025, 6, 10, 18, 0, 0)
        self.assertEqual(
            (reg_pass.event_begin_date, reg_pass.event_end_date),
            (self.event.date_begin, datetime(2025, 6, 10, 18, 0, 0)))

        # moving the ticket moves its registrations
        self.ticket_master.date_begin = datetime(2025, 6, 7, 9, 0, 0)
        self.assertEqual(reg_master.event_begin_date, datetime(2025, 6, 7, 9, 0, 0))

        # registrations are found by their own dates
        Registration = self.env['event.registration']
        self.assertEqual(
            Registration.search([('event_id', '=', self.event.id), ('event_begin_date', '<', self.event.date_begin)]),
            reg_master)
        self.assertEqual(
            Registration.search([('event_id', '=', self.event.id), ('event_end_date', '<', self.event.date_end)]),
            reg_pass | reg_master | reg_day_2)
        self.assertEqual(
            Registration.search([('event_id', '=', self.event.id), ('event_end_date', '>', datetime(2025, 6, 10, 20))]),
            reg_day_2)

    def test_registration_dates_slot_first(self):
        """ On multi-slot events, the slot gives the dates. """
        event = self.env['event.event'].create({
            'name': 'Festival',
            'date_begin': datetime(2025, 6, 10, 0, 0, 0),
            'date_end': datetime(2025, 6, 11, 23, 59, 59),
            'date_tz': 'UTC',
            'is_multi_slots': True,
            'event_slot_ids': [(0, 0, {'date': date(2025, 6, 11), 'start_hour': 9, 'end_hour': 18})],
            'event_ticket_ids': [(0, 0, {'name': 'Pass', 'date_begin': datetime(2025, 6, 10, 9, 0, 0)})],
        })
        registration = self.env['event.registration'].create({
            'event_id': event.id,
            'event_slot_id': event.event_slot_ids.id,
            'event_ticket_id': event.event_ticket_ids.id,
            'name': 'Attendee',
        })
        self.assertEqual(
            (registration.event_begin_date, registration.event_end_date),
            (event.event_slot_ids.start_datetime, event.event_slot_ids.end_datetime))

    def test_ticket_dates_coherency(self):
        with self.assertRaises(ValidationError):
            self.ticket_master.date_end = datetime(2025, 6, 7, 9, 0, 0)
        with self.assertRaises(ValidationError):
            # an open end falls back on the event end: still before the start
            self.ticket_pass.date_begin = datetime(2025, 6, 13, 9, 0, 0)

    def test_ticket_ics(self):
        ics = self.event._get_ics_file(ticket=self.ticket_master)[self.event.id]
        self.assertIn(b'20250608T090000', ics)
        self.assertIn(b'20250609T170000', ics)
        ics = self.event._get_ics_file()[self.event.id]
        self.assertIn(b'20250610T080000', ics)
