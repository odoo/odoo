# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime
from odoo.addons.calendar_bis.tests.test_common import TestCalendarCommon

class TestCalendarRecurrence(TestCalendarCommon):

    def _test_calendar_recurrence_options(self, vals, dates):
        event_ts = self.create_event({**vals, 'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id

        self.assertTrue(event.is_recurring, "Event should be set to recurring")
        self.assertEqual(len(event.timeslot_ids), len(dates), f"should have created {len(dates)} timeslots")
        self.assertEqual(event.timeslot_ids.sorted('start').mapped('start'), dates)
        return event

    def test_calendar_daily_recurrence(self):
        expected_dates = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 2, 10, 0),
            datetime(2024, 1, 3, 10, 0)
        ]
        recurring_vals = {
            'freq': 'daily',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
        }
        self._test_calendar_recurrence_options(recurring_vals, expected_dates)

    def test_calendar_weekly_recurrence(self):
        recurring_vals = {
            'freq': 'weekly',
            'mon': True,
            'tue': True,
            'count': 4,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
        }
        expected_dates = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 2, 10, 0),
            datetime(2024, 1, 8, 10, 0),
            datetime(2024, 1, 9, 10, 0),
        ]
        self._test_calendar_recurrence_options(recurring_vals, expected_dates)

    def test_calendar_monthly_recurrence(self):
        recurring_vals = {
            'freq': 'monthly',
            'monthday': 11,
            'count': 3,
            'start': datetime(2024, 1, 11, 10, 0),
            'stop': datetime(2024, 1, 11, 10, 30),
        }
        expected_dates = [
            datetime(2024, 1, 11, 10, 0),
            datetime(2024, 2, 11, 10, 0),
            datetime(2024, 3, 11, 10, 0),
        ]
        self._test_calendar_recurrence_options(recurring_vals, expected_dates)

    def test_calendar_monthly_weekday_recurrence(self):
        recurring_vals = {
            'freq': 'monthly',
            'monthweekday_n': 1,
            'monthweekday_day': 'mon',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
        }
        expected_dates = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 2, 5, 10, 0),
            datetime(2024, 3, 4, 10, 0),
        ]
        self._test_calendar_recurrence_options(recurring_vals, expected_dates)

    def test_calendar_yearly_recurrence(self):
        recurring_vals = {
            'freq': 'yearly',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
        }
        expected_dates = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2025, 1, 1, 10, 0),
            datetime(2026, 1, 1, 10, 0),
        ]
        self._test_calendar_recurrence_options(recurring_vals, expected_dates)

    def test_recurrence_until(self):
        recurring_vals = {
            'freq': 'daily',
            'until': datetime(2024, 1, 3, 10, 0),
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
        }
        expected_dates = [
            datetime(2024, 1, 1, 10, 0),
            datetime(2024, 1, 2, 10, 0),
            datetime(2024, 1, 3, 10, 0)
        ]
        self._test_calendar_recurrence_options(recurring_vals, expected_dates)

    def test_recurrence_forever(self):
        daily_recurring_event_ts = self.create_event({
            'name': 'Recurring Event',
            'is_recurring': True,
            'freq': 'daily',
            'start': datetime(2023, 1, 1, 10, 0),
            'stop': datetime(2023, 1, 1, 10, 30),
        })
        daily_recurring_event = daily_recurring_event_ts.event_id

        self.assertTrue(daily_recurring_event.is_recurring, "Event should be set to recurring")
        self.assertEqual(len(daily_recurring_event.timeslot_ids), 365, "should have created 365 timeslots")

    def test_private_recurring_event(self):
        event_ts = self.create_event({
            'name': "Recurring Private Event",
            'is_recurring': True,
            'freq': 'daily',
            'count': 2,
            'is_public': False,
            'start': datetime(2023, 1, 1, 10, 0),
            'stop': datetime(2023, 1, 1, 10, 30),
            'attendee_ids': [(0, 0, {'partner_id': user.partner_id.id}) for user in [self.calendar_user_A, self.calendar_user_B]]
        })
        self.assertEqual(len(event_ts.attendee_ids), 2, "should have 2 attendees")
        self.assertTrue(all(event.name == "Recurring Private Event" for event in event_ts.event_id.timeslot_ids), "User A can read all events in recurrence")
        self.assertTrue(
            all(event.name == "Recurring Private Event" for event in event_ts.event_id.timeslot_ids.with_user(self.calendar_user_B)),
            "User B can read all events in recurrence"
        )
        self.assertTrue(
            all(event.name == "Busy" for event in event_ts.event_id.timeslot_ids.with_user(self.calendar_user_C)),
            "User C should see all events as busy"
        )

        self.assertEqual(event_ts.event_id.timeslot_ids[-1].with_user(self.calendar_user_C).start, datetime(2023, 1, 2, 10, 0), "User C can read public fields")

    def test_break_recurrence_once(self):
        event_ts = self.create_event({
            'freq': 'daily',
            'until': datetime(2024, 1, 3, 10, 0),
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        new_event_once = event.exdate(event.timeslot_ids.sorted('start')[1])
        self.assertEqual(len(event.timeslot_ids), 2, "Old should only have 2 timeslots left")
        self.assertEqual(len(new_event_once.timeslot_ids), 1, "New should have 1 timeslots")
        self.assertEqual(new_event_once.is_recurring, False, "New should not be recurring")

        new_event_once.name = "New Event"
        self.assertEqual(event.name, "Recurring Event", "Old should not have been modified")
        self.assertEqual(new_event_once.name, "New Event", "New should have been modified")

        event.make_timeslots()
        new_event_once.make_timeslots()
        self.assertEqual(len(event.timeslot_ids), 2, "Old should still only have 2 timeslots left")
        self.assertEqual(len(new_event_once.timeslot_ids), 1, "New should still have 1 timeslots")

    def test_break_recurrence_after_until(self):
        event_ts = self.create_event({
            'freq': 'daily',
            'until': datetime(2024, 1, 3, 10, 0),
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        new_event_after = event.break_after(event.timeslot_ids.sorted('start')[1])
        self.assertEqual(len(event.timeslot_ids), 1, "Old should only have 1 timeslots left")
        self.assertEqual(len(new_event_after.timeslot_ids), 2, "New should have 2 timeslots")

        new_event_after.name = "New Event"
        self.assertEqual(event.name, "Recurring Event", "Old should not have been modified")
        self.assertEqual(new_event_after.name, "New Event", "New should have been modified")

        event.make_timeslots()
        new_event_after.make_timeslots()
        self.assertEqual(len(event.timeslot_ids), 1, "Old should still only have 1 timeslots left")
        self.assertEqual(len(new_event_after.timeslot_ids), 2, "New should still have 2 timeslots")

    def test_break_recurrence_after_count(self):
        event_ts = self.create_event({
            'freq': 'daily',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        new_event_after = event.break_after(event.timeslot_ids.sorted('start')[1])
        self.assertEqual(len(event.timeslot_ids), 1, "Old should only have 1 timeslots left")
        self.assertEqual(event.count, 1, "Count should be adapted accordingly")
        self.assertEqual(len(new_event_after.timeslot_ids), 2, "New should have 2 timeslots")
        self.assertEqual(new_event_after.count, 2, "Count should be adapted accordingly")

        new_event_after.name = "New Event"
        self.assertEqual(event.name, "Recurring Event", "Old should not have been modified")
        self.assertEqual(new_event_after.name, "New Event", "New should have been modified")

        event.make_timeslots()
        new_event_after.make_timeslots()
        self.assertEqual(len(event.timeslot_ids), 1, "Old should still only have 1 timeslots left")
        self.assertEqual(len(new_event_after.timeslot_ids), 2, "New should still have 2 timeslots")

    def test_edit_recurrence_one(self):
        event_ts = self.create_event({
            'freq': 'daily',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        ts = event.timeslot_ids.sorted('start')[1]
        ts.write({'name': 'New Name', 'edit':'one'})
        self.assertNotEqual(ts.event_id, event, "Timeslot should have been moved to a new event")
        self.assertEqual(ts.name, 'New Name', "Timeslot should have been modified")
        self.assertEqual(event.name, 'Recurring Event', "Old should not have been modified")
        self.assertEqual(len(event.timeslot_ids), 2, "Old should only have 2 timeslots left")
        self.assertEqual(len(ts.event_id.timeslot_ids), 1, "New should have 1 timeslots")

    def test_edit_recurrence_after(self):
        event_ts = self.create_event({
            'freq': 'daily',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        ts = event.timeslot_ids.sorted('start')[1]
        ts.write({'name': 'New Name', 'edit': 'post'})
        self.assertNotEqual(ts.event_id, event, "Timeslot should have been moved to a new event")
        self.assertEqual(ts.name, 'New Name', "Timeslot should have been modified")
        self.assertEqual(event.name, 'Recurring Event', "Old should not have been modified")
        self.assertEqual(len(event.timeslot_ids), 1, "Old should only have 1 timeslots left")
        self.assertEqual(len(ts.event_id.timeslot_ids), 2, "New should have 2 timeslots")

    def test_edit_recurrence_all(self):
        event_ts = self.create_event({
            'freq': 'daily',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        ts = event.timeslot_ids.sorted('start')[1]
        ts.write({'name': 'New Name', 'edit': 'all'})
        self.assertEqual(ts.event_id, event, "Timeslot shouldn't have a new timeslot")
        self.assertEqual(event.name, 'New Name', "Old should have been modified")

    def test_edit_recurrence_time(self):
        event_ts = self.create_event({
            'freq': 'daily',
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        ts = event.timeslot_ids.sorted('start')[1]
        ts.write({'start': datetime(2024, 1, 2, 9, 0), 'edit': 'all'})
        self.assertEqual(event.timeslot_ids.mapped('start'), [datetime(2024, 1, 1, 9, 0), datetime(2024, 1, 2, 9, 0), datetime(2024, 1, 3, 9, 0)], "")
        self.assertEqual(event.timeslot_ids.mapped('stop'), [datetime(2024, 1, 1, 10, 30), datetime(2024, 1, 2, 10, 30), datetime(2024, 1, 3, 10, 30)], "")
        self.assertEqual(event.timeslot_ids.mapped('duration'), [1.5, 1.5, 1.5], "")

    def test_edit_weekly_recurrence_day(self):
        event_ts = self.create_event({
            'freq': 'weekly',
            'mon': True,
            'count': 3,
            'start': datetime(2024, 1, 1, 10, 0),
            'stop': datetime(2024, 1, 1, 10, 30),
            'is_recurring': True, 'name': 'Recurring Event'})
        event = event_ts.event_id
        timeslots = event.timeslot_ids.sorted('start')
        self.assertEqual(timeslots.mapped('start'),
                         [datetime(2024, 1, 1, 10, 0), datetime(2024, 1, 8, 10, 0), datetime(2024, 1, 15, 10, 0)], "")
        self.assertEqual(timeslots.mapped('stop'),
                         [datetime(2024, 1, 1, 10, 30), datetime(2024, 1, 8, 10, 30), datetime(2024, 1, 15, 10, 30)], "")
        self.assertEqual((event.mon, event.tue), (True, False), "")
        event_ts.write({'start': datetime(2024, 1, 2, 10, 0), 'stop':datetime(2024, 1, 2, 10, 30), 'edit': 'all'})
        timeslots = event.timeslot_ids.sorted('start')
        self.assertEqual(timeslots.mapped('start'),
                         [datetime(2024, 1, 2, 10, 0), datetime(2024, 1, 9, 10, 0), datetime(2024, 1, 16, 10, 0)], "")
        self.assertEqual(timeslots.mapped('stop'),
                         [datetime(2024, 1, 2, 10, 30), datetime(2024, 1, 9, 10, 30), datetime(2024, 1, 16, 10, 30)], "")
        self.assertEqual((event.mon, event.tue), (False, True), "")
