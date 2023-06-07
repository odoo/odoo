# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
import pytz
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo.tests.common import TransactionCase
from freezegun import freeze_time


class TestRecurrentEvents(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super(TestRecurrentEvents, cls).setUpClass()
        lang = cls.env['res.lang']._lang_get(cls.env.user.lang)
        lang.week_start = '1'  # Monday

    def assertEventDates(self, events, dates):
        events = events.sorted('start')
        self.assertEqual(len(events), len(dates), "Wrong number of events in the recurrence")
        self.assertTrue(all(events.mapped('active')), "All events should be active")
        for event, dates in zip(events, dates):
            start, stop = dates
            self.assertEqual(event.start, start)
            self.assertEqual(event.stop, stop)


class TestCreateRecurrentEvents(TestRecurrentEvents):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.event = cls.env['calendar.event'].create({
            'name': 'Recurrent Event',
            'start': datetime(2019, 10, 21, 8, 0),
            'stop': datetime(2019, 10, 23, 18, 0),
            'recurrency': True,
        })

    def test_weekly_count(self):
        """ Every week, on Tuesdays, for 3 occurences """
        detached_events = self.event._apply_recurrence_values({
            'rrule_type': 'weekly',
            'tue': True,
            'interval': 1,
            'count': 3,
            'event_tz': 'UTC',
        })
        self.assertEqual(detached_events, self.event, "It should be detached from the recurrence")
        self.assertFalse(self.event.recurrence_id, "It should be detached from the recurrence")
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), 3, "It should have 3 events in the recurrence")
        self.assertEventDates(events, [
            (datetime(2019, 10, 22, 8, 0), datetime(2019, 10, 24, 18, 0)),
            (datetime(2019, 10, 29, 8, 0), datetime(2019, 10, 31, 18, 0)),
            (datetime(2019, 11, 5, 8, 0), datetime(2019, 11, 7, 18, 0)),
        ])

    def test_weekly_interval_2(self):
        self.event._apply_recurrence_values({
            'interval': 2,
            'rrule_type': 'weekly',
            'tue': True,
            'count': 2,
            'event_tz': 'UTC',
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEventDates(events, [
            (datetime(2019, 10, 22, 8, 0), datetime(2019, 10, 24, 18, 0)),
            (datetime(2019, 11, 5, 8, 0), datetime(2019, 11, 7, 18, 0)),
        ])

    def test_weekly_interval_2_week_start_sunday(self):
        lang = self.env['res.lang']._lang_get(self.env.user.lang)
        lang.week_start = '7'  # Sunday

        self.event._apply_recurrence_values({
            'interval': 2,
            'rrule_type': 'weekly',
            'tue': True,
            'count': 2,
            'event_tz': 'UTC',
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEventDates(events, [
            (datetime(2019, 10, 22, 8, 0), datetime(2019, 10, 24, 18, 0)),
            (datetime(2019, 11, 5, 8, 0), datetime(2019, 11, 7, 18, 0)),
        ])
        lang.week_start = '1'  # Monday

    def test_weekly_until(self):
        self.event._apply_recurrence_values({
            'rrule_type': 'weekly',
            'tue': True,
            'interval': 2,
            'end_type': 'end_date',
            'until': datetime(2019, 11, 15),
            'event_tz': 'UTC',
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), 2, "It should have 2 events in the recurrence")
        self.assertEventDates(events, [
            (datetime(2019, 10, 22, 8, 0), datetime(2019, 10, 24, 18, 0)),
            (datetime(2019, 11, 5, 8, 0), datetime(2019, 11, 7, 18, 0)),
        ])

    def test_monthly_count_by_date(self):
        self.event._apply_recurrence_values({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'date',
            'day': 27,
            'end_type': 'count',
            'count': 3,
            'event_tz': 'UTC',
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), 3, "It should have 3 events in the recurrence")
        self.assertEventDates(events, [
            (datetime(2019, 10, 27, 8, 0), datetime(2019, 10, 29, 18, 0)),
            (datetime(2019, 12, 27, 8, 0), datetime(2019, 12, 29, 18, 0)),
            (datetime(2020, 2, 27, 8, 0), datetime(2020, 2, 29, 18, 0)),
        ])

    def test_monthly_count_by_date_31(self):
        self.event._apply_recurrence_values({
            'rrule_type': 'monthly',
            'interval': 1,
            'month_by': 'date',
            'day': 31,
            'end_type': 'count',
            'count': 3,
            'event_tz': 'UTC',
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), 3, "It should have 3 events in the recurrence")
        self.assertEventDates(events, [
            (datetime(2019, 10, 31, 8, 0), datetime(2019, 11, 2, 18, 0)),
            # Missing 31th in November
            (datetime(2019, 12, 31, 8, 0), datetime(2020, 1, 2, 18, 0)),
            (datetime(2020, 1, 31, 8, 0), datetime(2020, 2, 2, 18, 0)),
        ])

    def test_monthly_until_by_day(self):
        """ Every 2 months, on the third Tuesday, until 27th March 2020 """
        self.event.start = datetime(2019, 10, 1, 8, 0)
        self.event.stop = datetime(2019, 10, 3, 18, 0)
        self.event._apply_recurrence_values({
            'rrule_type': 'monthly',
            'interval': 2,
            'month_by': 'day',
            'byday': '3',
            'weekday': 'TUE',
            'end_type': 'end_date',
            'until': date(2020, 3, 27),
            'event_tz': 'UTC',
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), 3, "It should have 3 events in the recurrence")
        self.assertEventDates(events, [
            (datetime(2019, 10, 15, 8, 0), datetime(2019, 10, 17, 18, 0)),
            (datetime(2019, 12, 17, 8, 0), datetime(2019, 12, 19, 18, 0)),
            (datetime(2020, 2, 18, 8, 0), datetime(2020, 2, 20, 18, 0)),
        ])

    def test_monthly_until_by_day_last(self):
        """ Every 2 months, on the last Wednesday, until 15th January 2020 """
        self.event._apply_recurrence_values({
            'interval': 2,
            'rrule_type': 'monthly',
            'month_by': 'day',
            'weekday': 'WED',
            'byday': '-1',
            'end_type': 'end_date',
            'until': date(2020, 1, 15),
            'event_tz': 'UTC',
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), 2, "It should have 3 events in the recurrence")
        self.assertEventDates(events, [
            (datetime(2019, 10, 30, 8, 0), datetime(2019, 11, 1, 18, 0)),
            (datetime(2019, 12, 25, 8, 0), datetime(2019, 12, 27, 18, 0)),
        ])

    def test_yearly_count(self):
        self.event._apply_recurrence_values({
            'interval': 2,
            'rrule_type': 'yearly',
            'count': 2,
            'event_tz': 'UTC',
        })
        events = self.event.recurrence_id.calendar_event_ids
        self.assertEqual(len(events), 2, "It should have 3 events in the recurrence")
        self.assertEventDates(events, [
            (self.event.start, self.event.stop),
            (self.event.start + relativedelta(years=2), self.event.stop + relativedelta(years=2)),
        ])

    def test_dst_timezone(self):
        """ Test hours stays the same, regardless of DST changes """
        self.event.start = datetime(2002, 10, 28, 10, 0)
        self.event.stop = datetime(2002, 10, 28, 12, 0)
        self.event._apply_recurrence_values({
            'interval': 2,
            'rrule_type': 'weekly',
            'mon': True,
            'count': '2',
            'event_tz': 'US/Eastern',  # DST change on 2002/10/27
        })
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2002, 10, 28, 10, 0), datetime(2002, 10, 28, 12, 0)),
            (datetime(2002, 11, 11, 10, 0), datetime(2002, 11, 11, 12, 0)),
        ])

    def test_ambiguous_dst_time_winter(self):
        """ Test hours stays the same, regardless of DST changes """
        eastern = pytz.timezone('US/Eastern')
        dt = eastern.localize(datetime(2002, 10, 20, 1, 30, 00)).astimezone(pytz.utc).replace(tzinfo=None)
        # Next occurence happens at 1:30am on 27th Oct 2002 which happened twice in the US/Eastern
        # timezone when the clocks where put back at the end of Daylight Saving Time
        self.event.start = dt
        self.event.stop = dt + relativedelta(hours=1)
        self.event._apply_recurrence_values({
            'interval': 1,
            'rrule_type': 'weekly',
            'sun': True,
            'count': '2',
            'event_tz': 'US/Eastern'  # DST change on 2002/4/7
        })
        events = self.event.recurrence_id.calendar_event_ids
        self.assertEqual(events.mapped('duration'), [1, 1])
        self.assertEventDates(events, [
            (datetime(2002, 10, 20, 5, 30), datetime(2002, 10, 20, 6, 30)),
            (datetime(2002, 10, 27, 6, 30), datetime(2002, 10, 27, 7, 30)),
        ])

    def test_ambiguous_dst_time_spring(self):
        """ Test hours stays the same, regardless of DST changes """
        eastern = pytz.timezone('US/Eastern')
        dt = eastern.localize(datetime(2002, 3, 31, 2, 30, 00)).astimezone(pytz.utc).replace(tzinfo=None)
        # Next occurence happens 2:30am on 7th April 2002 which never happened at all in the
        # US/Eastern timezone, as the clocks where put forward at 2:00am skipping the entire hour
        self.event.start = dt
        self.event.stop = dt + relativedelta(hours=1)
        self.event._apply_recurrence_values({
            'interval': 1,
            'rrule_type': 'weekly',
            'sun': True,
            'count': '2',
            'event_tz': 'US/Eastern'  # DST change on 2002/4/7
        })
        events = self.event.recurrence_id.calendar_event_ids
        self.assertEqual(events.mapped('duration'), [1, 1])
        # The event begins at "the same time" (i.e. 2h30 after midnight), but that day, 2h30 after midnight happens to be at 3:30 am
        self.assertEventDates(events, [
            (datetime(2002, 3, 31, 7, 30), datetime(2002, 3, 31, 8, 30)),
            (datetime(2002, 4, 7, 7, 30), datetime(2002, 4, 7, 8, 30)),
        ])

    def test_ambiguous_full_day(self):
        """ Test date stays the same, regardless of DST changes """
        self.event.write({
            'start': datetime(2020, 3, 23, 0, 0),
            'stop': datetime(2020, 3, 23, 23, 59),
        })
        self.event.allday = True
        self.event._apply_recurrence_values({
            'interval': 1,
            'rrule_type': 'weekly',
            'mon': True,
            'count': 2,
            'event_tz': 'Europe/Brussels'  # DST change on 2020/3/23
        })
        events = self.event.recurrence_id.calendar_event_ids
        self.assertEventDates(events, [
            (datetime(2020, 3, 23, 0, 0), datetime(2020, 3, 23, 23, 59)),
            (datetime(2020, 3, 30, 0, 0), datetime(2020, 3, 30, 23, 59)),
        ])

    def test_videocall_recurrency(self):
        self.event._set_discuss_videocall_location()
        self.event._apply_recurrence_values({
            'interval': 1,
            'rrule_type': 'weekly',
            'mon': True,
            'count': 2,
        })

        recurrent_events = self.event.recurrence_id.calendar_event_ids
        detached_events = self.event.recurrence_id.calendar_event_ids - self.event
        rec_events_videocall_locations = recurrent_events.mapped('videocall_location')
        self.assertEqual(len(rec_events_videocall_locations), len(set(rec_events_videocall_locations)), 'Recurrent events should have different videocall locations')
        self.assertEqual(not any(recurrent_events.videocall_channel_id), True, 'No channel should be set before the route is accessed')
        # create the first channel
        detached_events[0]._create_videocall_channel()
        # after channel is created, all other events should have the same channel
        self.assertEqual(detached_events[0].videocall_channel_id.id, self.event.videocall_channel_id.id)

    @freeze_time('2023-03-27')
    def test_backward_pass_dst(self):
        """
            When we apply the rule to compute the period of the recurrence,
            we take an earlier date (in `_get_start_of_period` method).
            However, it is possible that this earlier date has a different DST.
            This causes time difference problems.
        """
        # In Europe/Brussels: 26 March 2023 from winter to summer (from no DST to DST)
        # We are in the case where we create a recurring event after the time change (there is the DST).
        timezone = 'Europe/Brussels'
        tz = pytz.timezone(timezone)
        dt = tz.localize(datetime(2023, 3, 27, 9, 0, 00)).astimezone(pytz.utc).replace(tzinfo=None)
        self.event.start = dt
        self.event.stop = dt + relativedelta(hours=1)

        # Check before apply the recurrence
        self.assertEqual(self.event.start, datetime(2023, 3, 27, 7, 0, 00)) # Because 2023-03-27 in Europe/Brussels is UTC+2

        self.event._apply_recurrence_values({
            'rrule_type': 'monthly', # Because we will take the first day of the month (jump back)
            'interval': 1,
            'end_type': 'count',
            'count': 2, # To have the base event and the unique recurrence event
            'month_by': 'date',
            'day': 27,
            'event_tz': timezone,
        })

        # What we expect:
        #   - start date of base event: datetime(2023, 3, 27, 7, 0, 00)
        #   - start date of the unique recurrence event: datetime(2023, 4, 27, 7, 0, 00)

        # With the FIX, we replace the following lines with
        # `events = self.event.recurrence_id.calendar_event_ids`
        recurrence = self.env['calendar.recurrence'].search([('base_event_id', '=', self.event.id)])
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), 2, "It should have 2 events in the recurrence")
        self.assertIn(self.event, events)

        self.assertEventDates(events, [
            (datetime(2023, 3, 27, 7, 00), datetime(2023, 3, 27, 8, 00)),
            (datetime(2023, 4, 27, 7, 00), datetime(2023, 4, 27, 8, 00)),
        ])

class TestUpdateRecurrentEvents(TestRecurrentEvents):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        event = cls.env['calendar.event'].create({
            'name': 'Recurrent Event',
            'start': datetime(2019, 10, 22, 1, 0),
            'stop': datetime(2019, 10, 24, 18, 0),
            'recurrency': True,
            'rrule_type': 'weekly',
            'tue': True,
            'interval': 1,
            'count': 3,
            'event_tz': 'Etc/GMT-4',
        })
        cls.recurrence = event.recurrence_id
        cls.events = event.recurrence_id.calendar_event_ids.sorted('start')

    def test_shift_future(self):
        event = self.events[1]
        self.events[1].write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=5),
        })
        self.assertEqual(self.recurrence.end_type, 'end_date')
        self.assertEqual(self.recurrence.until, date(2019, 10, 27))
        self.assertEventDates(self.recurrence.calendar_event_ids, [
            (datetime(2019, 10, 22, 1, 0), datetime(2019, 10, 24, 18, 0)),
        ])
        new_recurrence = event.recurrence_id
        self.assertNotEqual(self.recurrence, new_recurrence)
        self.assertEqual(new_recurrence.count, 2)
        self.assertEqual(new_recurrence.dtstart, datetime(2019, 11, 2, 1, 0))
        self.assertFalse(new_recurrence.tue)
        self.assertTrue(new_recurrence.sat)
        self.assertEventDates(new_recurrence.calendar_event_ids, [
            (datetime(2019, 11, 2, 1, 0), datetime(2019, 11, 5, 18, 0)),
            (datetime(2019, 11, 9, 1, 0), datetime(2019, 11, 12, 18, 0)),
        ])

    def test_shift_future_first(self):
        event = self.events[0]
        self.events[0].write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=5),
        })
        new_recurrence = event.recurrence_id
        self.assertFalse(self.recurrence.exists())
        self.assertEqual(new_recurrence.count, 3)
        self.assertEqual(new_recurrence.dtstart, datetime(2019, 10, 26, 1, 0))
        self.assertFalse(new_recurrence.tue)
        self.assertTrue(new_recurrence.sat)
        self.assertEventDates(new_recurrence.calendar_event_ids, [
            (datetime(2019, 10, 26, 1, 0), datetime(2019, 10, 29, 18, 0)),
            (datetime(2019, 11, 2, 1, 0), datetime(2019, 11, 5, 18, 0)),
            (datetime(2019, 11, 9, 1, 0), datetime(2019, 11, 12, 18, 0)),
        ])

    def test_shift_reapply(self):
        event = self.events[2]
        self.events[2].write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=5),
        })
        # re-Applying the first recurrence should be idempotent
        self.recurrence._apply_recurrence()
        self.assertEventDates(self.recurrence.calendar_event_ids, [
            (datetime(2019, 10, 22, 1, 0), datetime(2019, 10, 24, 18, 0)),
            (datetime(2019, 10, 29, 1, 0), datetime(2019, 10, 31, 18, 0)),
        ])

    def test_shift_all(self):
        event = self.events[1]
        self.assertEventDates(event.recurrence_id.calendar_event_ids, [
            (datetime(2019, 10, 22, 1, 0), datetime(2019, 10, 24, 18, 0)),
            (datetime(2019, 10, 29, 1, 0), datetime(2019, 10, 31, 18, 0)),
            (datetime(2019, 11, 5, 1, 0), datetime(2019, 11, 7, 18, 0)),
        ])
        event.write({
            'recurrence_update': 'all_events',
            'tue': False,
            'fri': False,
            'sat': True,
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=5),
        })
        recurrence = self.env['calendar.recurrence'].search([])
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2019, 10, 26, 1, 0), datetime(2019, 10, 29, 18, 0)),
            (datetime(2019, 11, 2, 1, 0), datetime(2019, 11, 5, 18, 0)),
            (datetime(2019, 11, 9, 1, 0), datetime(2019, 11, 12, 18, 0)),
        ])

    def test_shift_stop_all(self):
        # testing the case where we only want to update the stop time
        event = self.events[0]
        event.write({
            'recurrence_update': 'all_events',
            'stop': event.stop + relativedelta(hours=1),
        })
        self.assertEventDates(event.recurrence_id.calendar_event_ids, [
            (datetime(2019, 10, 22, 2, 0), datetime(2019, 10, 24, 19, 0)),
            (datetime(2019, 10, 29, 2, 0), datetime(2019, 10, 31, 19, 0)),
            (datetime(2019, 11, 5, 2, 0), datetime(2019, 11, 7, 19, 0)),
        ])

    def test_change_week_day_rrule(self):
        recurrence = self.events.recurrence_id
        recurrence.rrule = 'FREQ=WEEKLY;COUNT=3;BYDAY=WE' # from TU to WE
        self.assertFalse(self.recurrence.tue)
        self.assertTrue(self.recurrence.wed)

    def test_shift_all_base_inactive(self):
        self.recurrence.base_event_id.active = False
        event = self.events[1]
        event.write({
            'recurrence_update': 'all_events',
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=5),
        })
        self.assertFalse(self.recurrence.calendar_event_ids, "Inactive event should not create recurrent events")

    def test_shift_all_with_outlier(self):
        outlier = self.events[1]
        outlier.write({
            'recurrence_update': 'self_only',
            'start': datetime(2019, 10, 31, 1, 0),  # Thursday
            'stop': datetime(2019, 10, 31, 18, 0),
        })
        event = self.events[0]
        event.write({
            'recurrence_update': 'all_events',
            'tue': False,
            'fri': False,
            'sat': True,
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=4),
        })
        self.assertEventDates(event.recurrence_id.calendar_event_ids, [
            (datetime(2019, 10, 26, 1, 0), datetime(2019, 10, 28, 18, 0)),
            (datetime(2019, 11, 2, 1, 0), datetime(2019, 11, 4, 18, 0)),
            (datetime(2019, 11, 9, 1, 0), datetime(2019, 11, 11, 18, 0))
        ])
        self.assertFalse(outlier.exists(), 'The outlier should have been deleted')

    def test_update_recurrence_future(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'future_events',
            'fri': True,  # recurrence is now Tuesday AND Friday
            'count': 4,
        })
        self.assertEventDates(self.recurrence.calendar_event_ids, [
            (datetime(2019, 10, 22, 1, 0), datetime(2019, 10, 24, 18, 0)),  # Tu
        ])

        self.assertEventDates(event.recurrence_id.calendar_event_ids, [
            (datetime(2019, 10, 29, 1, 0), datetime(2019, 10, 31, 18, 0)),  # Tu
            (datetime(2019, 11, 1, 1, 0), datetime(2019, 11, 3, 18, 0)),    # Fr
            (datetime(2019, 11, 5, 1, 0), datetime(2019, 11, 7, 18, 0)),    # Tu
            (datetime(2019, 11, 8, 1, 0), datetime(2019, 11, 10, 18, 0)),   # Fr
        ])

        events = event.recurrence_id.calendar_event_ids.sorted('start')
        self.assertEqual(events[0], self.events[1], "Events on Tuesdays should not have changed")
        self.assertEqual(events[2], self.events[2], "Events on Tuesdays should not have changed")
        self.assertNotEqual(events.recurrence_id, self.recurrence, "Events should no longer be linked to the original recurrence")
        self.assertEqual(events.recurrence_id.count, 4, "The new recurrence should have 4")
        self.assertTrue(event.recurrence_id.tue)
        self.assertTrue(event.recurrence_id.fri)

    def test_update_recurrence_all(self):
        self.events[1].write({
            'recurrence_update': 'all_events',
            'mon': True,  # recurrence is now Tuesday AND Monday
        })
        recurrence = self.env['calendar.recurrence'].search([])
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2019, 10, 22, 1, 0), datetime(2019, 10, 24, 18, 0)),
            (datetime(2019, 10, 28, 1, 0), datetime(2019, 10, 30, 18, 0)),
            (datetime(2019, 10, 29, 1, 0), datetime(2019, 10, 31, 18, 0)),
        ])

    def test_shift_single(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'self_only',
            'name': "Updated event",
            'start': event.start - relativedelta(hours=2)
        })
        self.events[0].write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(hours=4),
            'stop': event.stop + relativedelta(hours=5),
        })

    def test_break_recurrence_future(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'future_events',
            'recurrency': False,
        })
        self.assertFalse(event.recurrence_id)
        self.assertTrue(self.events[0].active)
        self.assertTrue(self.events[1].active)
        self.assertFalse(self.events[2].exists())
        self.assertEqual(self.recurrence.until, date(2019, 10, 27))
        self.assertEqual(self.recurrence.end_type, 'end_date')
        self.assertEventDates(self.recurrence.calendar_event_ids, [
            (datetime(2019, 10, 22, 1, 0), datetime(2019, 10, 24, 18, 0)),
        ])

    def test_break_recurrence_all(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'all_events',
            'recurrency': False,
            'count': 0,  # In practice, JS framework sends updated recurrency fields, since they have been recomputed, triggered by the `recurrency` change
        })
        self.assertFalse(self.events[0].exists())
        self.assertTrue(event.active)
        self.assertFalse(self.events[2].exists())
        self.assertFalse(event.recurrence_id)
        self.assertFalse(self.recurrence.exists())

    def test_all_day_shift(self):
        recurrence = self.env['calendar.event'].create({
            'name': 'Recurrent Event',
            'start_date': datetime(2019, 10, 22),
            'stop_date': datetime(2019, 10, 24),
            'recurrency': True,
            'rrule_type': 'weekly',
            'tue': True,
            'interval': 1,
            'count': 3,
            'event_tz': 'Etc/GMT-4',
            'allday': True,
        }).recurrence_id
        events = recurrence.calendar_event_ids.sorted('start')
        event = events[1]
        event.write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=5),
        })
        self.assertEqual(recurrence.end_type, 'end_date')
        self.assertEqual(recurrence.until, date(2019, 10, 27))
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2019, 10, 22, 8, 0), datetime(2019, 10, 24, 18, 0)),
        ])
        new_recurrence = event.recurrence_id
        self.assertNotEqual(recurrence, new_recurrence)
        self.assertEqual(new_recurrence.count, 2)
        self.assertEqual(new_recurrence.dtstart, datetime(2019, 11, 2, 8, 0))
        self.assertFalse(new_recurrence.tue)
        self.assertTrue(new_recurrence.sat)
        self.assertEventDates(new_recurrence.calendar_event_ids, [
            (datetime(2019, 11, 2, 8, 0), datetime(2019, 11, 5, 18, 0)),
            (datetime(2019, 11, 9, 8, 0), datetime(2019, 11, 12, 18, 0)),
        ])

    def test_archive_recurrence_all(self):
        self.events[1].action_mass_archive('all_events')
        self.assertEqual([False, False, False], self.events.mapped('active'))

    def test_archive_recurrence_future(self):
        event = self.events[1]
        event.action_mass_archive('future_events')
        self.assertEqual([True, False, False], self.events.mapped('active'))

    def test_unlink_recurrence_all(self):
        event = self.events[1]
        event.action_mass_deletion('all_events')
        self.assertFalse(self.recurrence.exists())
        self.assertFalse(self.events.exists())

    def test_unlink_recurrence_future(self):
        event = self.events[1]
        event.action_mass_deletion('future_events')
        self.assertTrue(self.recurrence)
        self.assertEqual(self.events.exists(), self.events[0])


class TestUpdateMultiDayWeeklyRecurrentEvents(TestRecurrentEvents):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        event = cls.env['calendar.event'].create({
            'name': 'Recurrent Event',
            'start': datetime(2019, 10, 22, 1, 0),
            'stop': datetime(2019, 10, 24, 18, 0),
            'recurrency': True,
            'rrule_type': 'weekly',
            'tue': True,
            'fri': True,
            'interval': 1,
            'count': 3,
            'event_tz': 'Etc/GMT-4',
        })
        cls.recurrence = event.recurrence_id
        cls.events = event.recurrence_id.calendar_event_ids.sorted('start')
        # Tuesday datetime(2019, 10, 22, 1, 0)
        # Friday datetime(2019, 10, 25, 1, 0)
        # Tuesday datetime(2019, 10, 29, 1, 0)

    def test_shift_all_multiple_weekdays(self):
        event = self.events[0]  # Tuesday
        # We go from 2 days a week Thuesday and Friday to one day a week, Thursday
        event.write({
            'recurrence_update': 'all_events',
            'tue': False,
            'thu': True,
            'fri': False,
            'start': event.start + relativedelta(days=2),
            'stop': event.stop + relativedelta(days=2),
        })
        recurrence = self.env['calendar.recurrence'].search([])
        # We don't try to do magic tricks. First event is moved, other remain
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2019, 10, 24, 1, 0), datetime(2019, 10, 26, 18, 0)),
            (datetime(2019, 10, 31, 1, 0), datetime(2019, 11, 2, 18, 0)),
            (datetime(2019, 11, 7, 1, 0), datetime(2019, 11, 9, 18, 0)),
        ])

    def test_shift_all_multiple_weekdays_duration(self):
        event = self.events[0]  # Tuesday
        event.write({
            'recurrence_update': 'all_events',
            'tue': False,
            'thu': True,
            'fri': False,
            'start': event.start + relativedelta(days=2),
            'stop': event.stop + relativedelta(days=3),
        })
        recurrence = self.env['calendar.recurrence'].search([])
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2019, 10, 24, 1, 0), datetime(2019, 10, 27, 18, 0)),
            (datetime(2019, 10, 31, 1, 0), datetime(2019, 11, 3, 18, 0)),
            (datetime(2019, 11, 7, 1, 0), datetime(2019, 11, 10, 18, 0)),
        ])

    def test_shift_future_multiple_weekdays(self):
        event = self.events[1]  # Friday
        event.write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(days=3),
            'stop': event.stop + relativedelta(days=3),
        })
        self.assertTrue(self.recurrence.fri)
        self.assertTrue(self.recurrence.tue)
        self.assertTrue(event.recurrence_id.tue)
        self.assertTrue(event.recurrence_id.mon)
        self.assertFalse(event.recurrence_id.fri)
        self.assertEqual(event.recurrence_id.count, 2)


class TestUpdateMonthlyByDay(TestRecurrentEvents):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        event = cls.env['calendar.event'].create({
            'name': 'Recurrent Event',
            'start': datetime(2019, 10, 15, 1, 0),
            'stop': datetime(2019, 10, 16, 18, 0),
            'recurrency': True,
            'rrule_type': 'monthly',
            'interval': 1,
            'count': 3,
            'month_by': 'day',
            'weekday': 'TUE',
            'byday': '3',
            'event_tz': 'Etc/GMT-4',
        })
        cls.recurrence = event.recurrence_id
        cls.events = event.recurrence_id.calendar_event_ids.sorted('start')
        # datetime(2019, 10, 15, 1, 0)
        # datetime(2019, 11, 19, 1, 0)
        # datetime(2019, 12, 17, 1, 0)

    def test_shift_all(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'all_events',
            'start': event.start + relativedelta(hours=5),
            'stop': event.stop + relativedelta(hours=5),
        })
        recurrence = self.env['calendar.recurrence'].search([])
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2019, 10, 15, 6, 0), datetime(2019, 10, 16, 23, 0)),
            (datetime(2019, 11, 19, 6, 0), datetime(2019, 11, 20, 23, 0)),
            (datetime(2019, 12, 17, 6, 0), datetime(2019, 12, 18, 23, 0)),
        ])


class TestUpdateMonthlyByDate(TestRecurrentEvents):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        event = cls.env['calendar.event'].create({
            'name': 'Recurrent Event',
            'start': datetime(2019, 10, 22, 1, 0),
            'stop': datetime(2019, 10, 24, 18, 0),
            'recurrency': True,
            'rrule_type': 'monthly',
            'interval': 1,
            'count': 3,
            'month_by': 'date',
            'day': 22,
            'event_tz': 'Etc/GMT-4',
        })
        cls.recurrence = event.recurrence_id
        cls.events = event.recurrence_id.calendar_event_ids.sorted('start')
        # datetime(2019, 10, 22, 1, 0)
        # datetime(2019, 11, 22, 1, 0)
        # datetime(2019, 12, 22, 1, 0)

    def test_shift_future(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(days=4),
            'stop': event.stop + relativedelta(days=5),
        })
        self.assertEventDates(self.recurrence.calendar_event_ids, [
            (datetime(2019, 10, 22, 1, 0), datetime(2019, 10, 24, 18, 0)),
        ])
        self.assertEventDates(event.recurrence_id.calendar_event_ids, [
            (datetime(2019, 11, 26, 1, 0), datetime(2019, 11, 29, 18, 0)),
            (datetime(2019, 12, 26, 1, 0), datetime(2019, 12, 29, 18, 0)),
        ])

    def test_update_all(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'all_events',
            'day': 25,
        })
        recurrence = self.env['calendar.recurrence'].search([('day', '=', 25)])
        self.assertEventDates(recurrence.calendar_event_ids, [
            (datetime(2019, 10, 25, 1, 0), datetime(2019, 10, 27, 18, 0)),
            (datetime(2019, 11, 25, 1, 0), datetime(2019, 11, 27, 18, 0)),
            (datetime(2019, 12, 25, 1, 0), datetime(2019, 12, 27, 18, 0)),
        ])
