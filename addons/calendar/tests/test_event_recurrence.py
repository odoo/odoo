# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.exceptions import UserError
import pytz
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

from odoo.tests.common import SavepointCase


class TestRecurrentEvents(SavepointCase):

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
            'tu': True,
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
            'tu': True,
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
            'tu': True,
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
            'tu': True,
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
            'weekday': 'TU',
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
            'weekday': 'WE',
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
            'mo': True,
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
            'su': True,
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
            'su': True,
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
            'mo': True,
            'count': 2,
            'event_tz': 'Europe/Brussels'  # DST change on 2020/3/23
        })
        events = self.event.recurrence_id.calendar_event_ids
        self.assertEventDates(events, [
            (datetime(2020, 3, 23, 0, 0), datetime(2020, 3, 23, 23, 59)),
            (datetime(2020, 3, 30, 0, 0), datetime(2020, 3, 30, 23, 59)),
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
            'tu': True,
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
        self.assertFalse(new_recurrence.tu)
        self.assertTrue(new_recurrence.sa)
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
        self.assertFalse(new_recurrence.tu)
        self.assertTrue(new_recurrence.sa)
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
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'start': event.start + relativedelta(days=4),
                'stop': event.stop + relativedelta(days=5),
            })

    def test_change_week_day_rrule(self):
        recurrence = self.events.recurrence_id
        recurrence.rrule = 'FREQ=WEEKLY;COUNT=3;BYDAY=WE' # from TU to WE
        self.assertFalse(self.recurrence.tu)
        self.assertTrue(self.recurrence.we)

    def test_shift_all_base_inactive(self):
        self.recurrence.base_event_id.active = False
        event = self.events[1]
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'start': event.start + relativedelta(days=4),
                'stop': event.stop + relativedelta(days=5),
            })

    def test_shift_all_with_outlier(self):
        outlier = self.events[1]
        outlier.write({
            'recurrence_update': 'self_only',
            'start': datetime(2019, 9, 26, 1, 0),  # Thursday
            'stop': datetime(2019, 9, 26, 18, 0),
        })
        event = self.events[0]
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'start': event.start + relativedelta(days=4),
                'stop': event.stop + relativedelta(days=5),
            })

    def test_update_recurrence_future(self):
        event = self.events[1]
        event.write({
            'recurrence_update': 'future_events',
            'fr': True,  # recurrence is now Tuesday AND Friday
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
        self.assertTrue(event.recurrence_id.tu)
        self.assertTrue(event.recurrence_id.fr)

    def test_update_recurrence_all(self):
        with self.assertRaises(UserError):
            self.events[1].write({
                'recurrence_update': 'all_events',
                'mo': True,  # recurrence is now Tuesday AND Monday
            })

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
            'tu': True,
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
        self.assertFalse(new_recurrence.tu)
        self.assertTrue(new_recurrence.sa)
        self.assertEventDates(new_recurrence.calendar_event_ids, [
            (datetime(2019, 11, 2, 8, 0), datetime(2019, 11, 5, 18, 0)),
            (datetime(2019, 11, 9, 8, 0), datetime(2019, 11, 12, 18, 0)),
        ])

    # TODO test followers, and alarms are copied


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
            'tu': True,
            'fr': True,
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
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'start': event.start + relativedelta(days=2),
                'stop': event.stop + relativedelta(days=2),
            })

    def test_shift_all_multiple_weekdays_duration(self):
        event = self.events[0]  # Tuesday
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'start': event.start + relativedelta(days=2),
                'stop': event.stop + relativedelta(days=3),
            })

    def test_shift_future_multiple_weekdays(self):
        event = self.events[1]  # Friday
        event.write({
            'recurrence_update': 'future_events',
            'start': event.start + relativedelta(days=3),
            'stop': event.stop + relativedelta(days=3),
        })
        self.assertTrue(self.recurrence.fr)
        self.assertTrue(self.recurrence.tu)
        self.assertTrue(event.recurrence_id.tu)
        self.assertTrue(event.recurrence_id.mo)
        self.assertFalse(event.recurrence_id.fr)
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
            'weekday': 'TU',
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
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'start': event.start - relativedelta(days=5),
                'stop': event.stop - relativedelta(days=4),
            })


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

    def test_shift_all(self):
        event = self.events[1]
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'start': event.start + relativedelta(days=4),
                'stop': event.stop + relativedelta(days=5),
            })

    def test_update_all(self):
        event = self.events[1]
        with self.assertRaises(UserError):
            event.write({
                'recurrence_update': 'all_events',
                'day': 25,
            })
