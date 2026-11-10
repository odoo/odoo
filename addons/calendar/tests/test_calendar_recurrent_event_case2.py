# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime

from freezegun import freeze_time

from odoo.addons.calendar.models.calendar_recurrence import MAX_RECURRENT_EVENT
from odoo.tests import common


class TestRecurrentEvent(common.TransactionCase):

    def setUp(self):
        super(TestRecurrentEvent, self).setUp()

        self.CalendarEvent = self.env['calendar.event']

    def test_recurrent_meeting1(self):
        # In order to test recurrent meetings in Odoo, I create meetings with different recurrence using different test cases.
        # I create a recurrent meeting with daily recurrence and fixed amount of time.
        self.CalendarEvent.create({
            'count': 5,
            'start': '2011-04-13 11:04:00',
            'stop': '2011-04-13 12:04:00',
            'duration': 1.0,
            'name': 'Test Meeting',
            'recurrency': True,
            'rrule_type': 'daily',
        })
        # I search for all the recurrent meetings
        meetings_count = self.CalendarEvent.with_context({'virtual_id': True}).search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2011-05-13')
        ])
        self.assertEqual(meetings_count, 5, 'Recurrent daily meetings are not created!')

    def test_recurrent_meeting2(self):
        # I create a weekly meeting till a particular end date.
        self.CalendarEvent.create({
            'start': '2011-04-18 11:47:00',
            'stop': '2011-04-18 12:47:00',
            'day': 1,
            'duration': 1.0,
            'until': '2011-04-30',
            'end_type': 'end_date',
            'fri': True,
            'mon': True,
            'thu': True,
            'tue': True,
            'wed': True,
            'name': 'Review code with programmer',
            'recurrency': True,
            'rrule_type': 'weekly',
        })

        # I search for all the recurrent weekly meetings.
        meetings_count = self.CalendarEvent.search_count([
            ('start', '>=', '2011-03-13'), ('stop', '<=', '2011-05-13')
        ])
        self.assertEqual(meetings_count, 10, 'Recurrent weekly meetings are not created!')

    @freeze_time('2026-04-01 05:00:00')
    def test_recurrent_meeting3(self):
        """
        Test that 'forever' recurrences are limited to a certain number of years (default 15).
        The default limit can be change by the system parameter `calendar.max_recurrence_years`.
        """
        values = {
            'duration': 1.0,
            'end_type': 'forever',
            'start': '2026-04-01 05:00:00',
            'stop': '2026-04-01 06:00:00',
            'recurrency': True,
        }
        for rrule_type, name, expected_count in (
            ('daily', 'Daily Meeting', 720),
            ('monthly', 'Monthly Meeting', 180),
            ('yearly', 'Yearly Meeting', 15),
        ):
            with self.subTest(rrule_type=rrule_type):
                self.CalendarEvent.create(dict(values, name=name, rrule_type=rrule_type))
                meetings_count = self.CalendarEvent.search_count([('name', '=', name)])
                self.assertEqual(
                    meetings_count,
                    expected_count,
                    f'Recurrent {rrule_type} meetings should be created and not exceed {expected_count}!',
                )

        # Edit the max recurrence years
        self.env['ir.config_parameter'].sudo().set_param('calendar.max_recurrence_years', 5)
        for rrule_type, name, expected_count in (
            ('daily', 'Custom Daily Meeting', 720),
            ('monthly', 'Custom Monthly Meeting', 60),
            ('yearly', 'Custom Yearly Meeting', 5),
        ):
            with self.subTest(rrule_type=rrule_type):
                self.CalendarEvent.create(dict(values, name=name, rrule_type=rrule_type))
                meetings_count = self.CalendarEvent.search_count([('name', '=', name)])
                self.assertEqual(
                    meetings_count,
                    expected_count,
                    f'Recurrent {rrule_type} meetings should be created and not exceed {expected_count}!',
                )

        # Weekly 'forever' must honor the limit too (instead of always hitting the
        # 720 hard cap), and the number of occurrences scales with the number of
        # selected weekdays and inversely with the interval. The start (2026-04-01)
        # is a Wednesday and the 2-year horizon ends on Saturday 2028-04-01.
        self.env['ir.config_parameter'].sudo().set_param('calendar.max_recurrence_years', 2)

        def weekly_count(name, **additional_values):
            event = self.CalendarEvent.create(dict(values, name=name, rrule_type='weekly', **additional_values))
            return len(event.recurrence_id.calendar_event_ids)

        # One weekday: every Wednesday up to 2028-03-29.
        self.assertEqual(weekly_count('Weekly One Day', wed=True), 105,
                         "weekly forever should respect max_recurrence_years, not the 720 cap")
        # Three weekdays: three per week, minus the Monday preceding the Wednesday start.
        self.assertEqual(weekly_count('Weekly Three Days', mon=True, wed=True, fri=True), 314,
                         "weekly count must scale with the number of selected weekdays")
        # interval=2: every other week.
        self.assertEqual(weekly_count('Weekly Interval Two', wed=True, interval=2), 53,
                         "weekly count must scale inversely with the interval")

        # Other side of the limit: a 5-year, 7-weekday horizon would generate ~1820
        # occurrences, so the hard cap holds the upcoming ones at MAX_RECURRENT_EVENT.
        self.env['ir.config_parameter'].sudo().set_param('calendar.max_recurrence_years', 5)
        capped = weekly_count('Weekly Capped', mon=True, tue=True, wed=True,
                              thu=True, fri=True, sat=True, sun=True)
        self.assertEqual(capped, MAX_RECURRENT_EVENT,
                         "weekly forever must clamp to the hard cap when the horizon "
                         "would exceed it")

    def _create_weekly_forever_event(self, start, **values):
        return self.CalendarEvent.create(dict({
            'name': 'Weekly Meeting',
            'start': start,
            'stop': start.replace(hour=start.hour + 1),
            'recurrency': True,
            'rrule_type': 'weekly',
            'wed': True,
            'end_type': 'forever',
            'event_tz': 'UTC',
        }, **values))

    @freeze_time('2026-04-01 05:00:00')
    def test_forever_recurrence_moving_horizon(self):
        """A 'forever' recurrence keeps an open-ended rule and creates its occurrences
        up to `calendar.max_recurrence_years` after now, even if it started long ago.
        """
        self.env['ir.config_parameter'].sudo().set_param('calendar.max_recurrence_years', 2)
        recurrence = self._create_weekly_forever_event(datetime(2024, 4, 3, 5)).recurrence_id

        self.assertEqual(recurrence.end_type, 'forever')
        self.assertNotIn('COUNT', recurrence.rrule)
        starts = recurrence.calendar_event_ids.mapped('start')
        self.assertEqual(min(starts), datetime(2024, 4, 3, 5))
        self.assertEqual(max(starts), datetime(2028, 3, 29, 5))

    @freeze_time('2026-04-01 05:00:00')
    def test_forever_recurrence_started_long_ago(self):
        """An endless recurrence that started long ago creates at most MAX_RECURRENT_EVENT
        past occurrences (the most recent ones) and keeps its first event.
        """
        event = self.CalendarEvent.create({
            'name': 'Daily Meeting',
            'start': datetime(2020, 1, 15, 5),
            'stop': datetime(2020, 1, 15, 6),
            'recurrency': True,
            'rrule_type': 'daily',
            'end_type': 'forever',
            'event_tz': 'UTC',
        })
        events = event.recurrence_id.calendar_event_ids
        past_events = events.filtered(lambda e: e.start < datetime(2026, 4, 1, 5))
        self.assertIn(event, events)
        self.assertEqual(len(past_events), MAX_RECURRENT_EVENT + 1)
        self.assertEqual(len(events - past_events), MAX_RECURRENT_EVENT)

    @freeze_time('2026-04-01 05:00:00')
    def test_forever_recurrence_lower_horizon(self):
        """Lowering `calendar.max_recurrence_years` keeps in the recurrence the
        occurrences already created beyond the new horizon.
        """
        recurrence = self._create_weekly_forever_event(datetime(2025, 1, 1, 5)).recurrence_id
        events = recurrence.calendar_event_ids
        self.assertGreater(max(events.mapped('start')), datetime(2040, 1, 1))

        self.env['ir.config_parameter'].sudo().set_param('calendar.max_recurrence_years', 2)
        recurrence._apply_recurrence()

        self.assertEqual(recurrence.calendar_event_ids, events)
        self.assertFalse(recurrence._get_outliers())
        self.assertFalse(self.CalendarEvent.search([('name', '=', 'Weekly Meeting'), ('recurrence_id', '=', False)]))

    def test_cron_extend_forever_recurrences(self):
        self.patch(self.registry['ir.cron'], '_commit_progress', lambda self, processed=0, remaining=None, **kwargs: 1)
        self.env['ir.config_parameter'].sudo().set_param('calendar.max_recurrence_years', 2)
        partner = self.env['res.partner'].create({'name': 'Attendee', 'email': 'attendee@example.com'})
        with freeze_time('2026-04-01 05:00:00'):
            event = self._create_weekly_forever_event(datetime(2026, 4, 1, 5), partner_ids=[partner.id])
        recurrence = event.recurrence_id
        events = recurrence.calendar_event_ids
        self.assertEqual(max(events.mapped('start')), datetime(2028, 3, 29, 5))

        with freeze_time('2026-04-20 05:00:00'):
            self.env['calendar.recurrence']._cron_extend_forever_recurrences()
        self.assertEqual(recurrence.calendar_event_ids, events, "The last occurrence is within the margin")

        mail_count = self.env['mail.mail'].search_count([])
        with freeze_time('2026-07-01 05:00:00'):
            self.env['calendar.recurrence']._cron_extend_forever_recurrences()
        new_events = recurrence.calendar_event_ids - events
        self.assertEqual(len(new_events), 13)
        self.assertEqual(max(new_events.mapped('start')), datetime(2028, 6, 28, 5))
        self.assertTrue(all(e.partner_ids == event.partner_ids for e in new_events))
        self.assertEqual(self.env['mail.mail'].search_count([]), mail_count, "No invitation is sent")

    def test_cron_extend_forever_recurrences_no_past_gap(self):
        """The cron does not create the occurrences missing between the last one and now."""
        self.patch(self.registry['ir.cron'], '_commit_progress', lambda self, processed=0, remaining=None, **kwargs: 1)
        self.env['ir.config_parameter'].sudo().set_param('calendar.max_recurrence_years', 2)
        with freeze_time('2026-04-01 05:00:00'):
            event = self._create_weekly_forever_event(datetime(2026, 4, 1, 5))
        recurrence = event.recurrence_id
        events = recurrence.calendar_event_ids
        self.assertEqual(max(events.mapped('start')), datetime(2028, 3, 29, 5))

        with freeze_time('2029-01-03 05:00:00'):
            self.env['calendar.recurrence']._cron_extend_forever_recurrences()
        new_events = recurrence.calendar_event_ids - events
        self.assertEqual(min(new_events.mapped('start')), datetime(2029, 1, 3, 5))
        self.assertEqual(max(new_events.mapped('start')), datetime(2031, 1, 1, 5))

    def test_cron_extend_forever_recurrences_capped(self):
        """A recurrence holding MAX_RECURRENT_EVENT upcoming occurrences is skipped,
        and gets one more occurrence for each one that becomes past.
        """
        self.patch(self.registry['ir.cron'], '_commit_progress', lambda self, processed=0, remaining=None, **kwargs: 1)
        with freeze_time('2026-04-01 05:00:00'):
            event = self._create_weekly_forever_event(datetime(2026, 4, 1, 5), rrule_type='daily')
        recurrence = event.recurrence_id
        events = recurrence.calendar_event_ids
        self.assertEqual(len(events), MAX_RECURRENT_EVENT)

        extended = []
        CalendarRecurrence = self.registry['calendar.recurrence']
        extend = CalendarRecurrence._extend_forever_occurrences

        def _extend_forever_occurrences(self):
            extended.extend(self.ids)
            return extend(self)
        self.patch(CalendarRecurrence, '_extend_forever_occurrences', _extend_forever_occurrences)

        with freeze_time('2026-04-01 05:00:00'):
            self.env['calendar.recurrence']._cron_extend_forever_recurrences()
        self.assertNotIn(recurrence.id, extended)

        with freeze_time('2026-04-03 05:00:00'):
            self.env['calendar.recurrence']._cron_extend_forever_recurrences()
        new_events = recurrence.calendar_event_ids - events
        self.assertEqual(sorted(new_events.mapped('start')), [datetime(2028, 3, 21, 5), datetime(2028, 3, 22, 5)])
