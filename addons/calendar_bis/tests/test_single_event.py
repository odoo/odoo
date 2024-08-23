# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime
from odoo.addons.calendar_bis.tests.test_common import TestCalendarCommon
from odoo.exceptions import AccessError


class TestCalendar(TestCalendarCommon):

    def test_calendar_event_bis_private_owner(self):
        single_event = self.single_event.with_user(self.calendar_user_A)
        self.assertEqual(single_event.can_read_private, True)
        self.assertEqual(single_event.can_write, True)

        self.assertEqual(single_event.name, 'EVENT 1')
        self.assertEqual(single_event.description, 'DESCRIPTION')
        self.assertEqual(single_event.is_public, False)
        self.assertEqual(single_event.is_recurring, False)
        self.assertEqual(len(single_event.event_id.timeslot_ids), 1)
        self.assertEqual(single_event.start, datetime(2024, 1, 1, 10, 0))
        self.assertEqual(single_event.stop, datetime(2024, 1, 1, 11, 0))
        self.assertEqual(single_event.duration, 1)

        # Assert No error when writing on the event
        single_event.write({'name': 'EVENT 1 BIS'})
        # Assert No error when writing on the timeslot
        single_event.write({'start': datetime(2024, 1, 1, 9, 0)})

    def test_calendar_event_bis_private_attendee(self):
        single_event = self.single_event.with_user(self.calendar_user_B)
        self.assertEqual(single_event.can_read_private, True)
        self.assertEqual(single_event.can_write, False)

        self.assertEqual(single_event.name, 'EVENT 1')
        self.assertEqual(single_event.description, 'DESCRIPTION')
        self.assertEqual(single_event.is_public, False)
        self.assertEqual(single_event.is_recurring, False)
        self.assertEqual(len(single_event.event_id.timeslot_ids), 1)
        self.assertEqual(single_event.start, datetime(2024, 1, 1, 10, 0))
        self.assertEqual(single_event.stop, datetime(2024, 1, 1, 11, 0))
        self.assertEqual(single_event.duration, 1)

        with self.assertRaises(AccessError):
            single_event.write({'name': 'EVENT 1 BIS'})

        with self.assertRaises(AccessError):
            single_event.write({'start': datetime(2024, 1, 1, 9, 0)})

    def test_calendar_event_bis_private_no_access(self):
        single_event = self.single_event.with_user(self.calendar_user_C)
        self.assertEqual(single_event.can_read_private, False)
        self.assertEqual(single_event.can_write, False)

        self.assertEqual(single_event.name, 'Busy')
        self.assertEqual(single_event.description, False)
        self.assertEqual(single_event.is_public, False)
        self.assertEqual(single_event.start, datetime(2024, 1, 1, 10, 0))
        self.assertEqual(single_event.stop, datetime(2024, 1, 1, 11, 0))
        self.assertEqual(single_event.duration, 1)

        with self.assertRaises(AccessError):
            single_event.write({'name': 'EVENT 1 BIS'})

        with self.assertRaises(AccessError):
            single_event.write({'start': datetime(2024, 1, 1, 9, 0)})

    def test_calendar_event_bis_public_owner(self):
        public_event = self.public_event.with_user(self.calendar_user_A)
        self.assertEqual(public_event.can_read_private, True)
        self.assertEqual(public_event.can_write, True)

        self.assertEqual(public_event.name, 'PUBLIC EVENT')
        self.assertEqual(public_event.description, 'DESCRIPTION')
        self.assertEqual(public_event.is_public, True)
        self.assertEqual(public_event.is_recurring, False)
        self.assertEqual(len(public_event.event_id.timeslot_ids), 1)
        self.assertEqual(public_event.start, datetime(2024, 1, 3, 15, 0))
        self.assertEqual(public_event.stop, datetime(2024, 1, 3, 16, 0))
        self.assertEqual(public_event.duration, 1)

        # Assert No error when writing on the event
        public_event.write({'name': 'PUBLIC EVENT BIS'})
        # Assert No error when writing on the timeslot
        public_event.write({'start': datetime(2024, 1, 3, 9, 0)})

    def test_calendar_event_bis_public_attendee(self):
        public_event = self.public_event.with_user(self.calendar_user_B)
        self.assertEqual(public_event.can_read_private, True)
        self.assertEqual(public_event.can_write, False)

        self.assertEqual(public_event.name, 'PUBLIC EVENT')
        self.assertEqual(public_event.description, 'DESCRIPTION')
        self.assertEqual(public_event.is_public, True)
        self.assertEqual(public_event.is_recurring, False)
        self.assertEqual(len(public_event.event_id.timeslot_ids), 1)
        self.assertEqual(public_event.start, datetime(2024, 1, 3, 15, 0))
        self.assertEqual(public_event.stop, datetime(2024, 1, 3, 16, 0))
        self.assertEqual(public_event.duration, 1)

        with self.assertRaises(AccessError):
            public_event.write({'name': 'PUBLIC EVENT BIS'})

        with self.assertRaises(AccessError):
            public_event.write({'start': datetime(2024, 1, 3, 9, 0)})

    def test_calendar_event_bis_public_no_access(self):
        public_event = self.public_event.with_user(self.calendar_user_C)
        self.assertEqual(public_event.can_read_private, True)
        self.assertEqual(public_event.can_write, False)

        self.assertEqual(public_event.name, 'PUBLIC EVENT')
        self.assertEqual(public_event.description, 'DESCRIPTION')
        self.assertEqual(public_event.is_public, True)
        self.assertEqual(public_event.start, datetime(2024, 1, 3, 15, 0))
        self.assertEqual(public_event.stop, datetime(2024, 1, 3, 16, 0))
        self.assertEqual(public_event.duration, 1)

        with self.assertRaises(AccessError):
            public_event.write({'name': 'PUBLIC EVENT BIS'})

        with self.assertRaises(AccessError):
            public_event.write({'start': datetime(2024, 1, 3, 9, 0)})
