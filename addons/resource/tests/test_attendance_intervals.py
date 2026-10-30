# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, timedelta

from odoo.tests.common import TransactionCase


class TestCalendarAttendanceIntervals(TransactionCase):
    """Tests for resource.calendar._attendance_intervals (the "New API" method)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Monday 2026-01-05 .. Sunday 2026-01-11
        cls.monday = date(2026, 1, 5)
        cls.sunday = date(2026, 1, 11)

    def _times(self, calendar, dt_from, dt_to, **kwargs):
        intervals = calendar._attendance_intervals(dt_from, dt_to, **kwargs)[calendar]
        return [(start, stop) for start, stop, dummy_attendance in intervals]

    def test_fixed_calendar_40h_week(self):
        """A standard Mon-Fri, 8-12 / 13-17 calendar returns 2 intervals per weekday, none on week-ends."""
        calendar = self.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour, 'hour_to': hour + 4})
                for day in range(5) for hour in (8, 13)
            ],
        })
        result = self._times(
            calendar,
            datetime.combine(self.monday, datetime.min.time()),
            datetime.combine(self.sunday, datetime.max.time()),
        )
        expected = [
            (datetime.combine(self.monday + timedelta(days=offset), datetime.min.time()) + timedelta(hours=hour),
             datetime.combine(self.monday + timedelta(days=offset), datetime.min.time()) + timedelta(hours=hour + 4))
            for offset in range(5) for hour in (8, 13)
        ]
        self.assertEqual(result, expected, "5 week days should each have a morning and afternoon interval, no week-end")

    def test_fixed_calendar_part_time(self):
        """A part-timer working Mon/Wed/Fri mornings only should only get intervals on those 3 days."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Part time 12h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': 8, 'hour_to': 12})
                for day in (0, 2, 4)  # Monday, Wednesday, Friday
            ],
        })
        result = self._times(
            calendar,
            datetime.combine(self.monday, datetime.min.time()),
            datetime.combine(self.sunday, datetime.max.time()),
        )
        self.assertEqual(result, [
            (datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 12, 0)),
            (datetime(2026, 1, 7, 8, 0), datetime(2026, 1, 7, 12, 0)),
            (datetime(2026, 1, 9, 8, 0), datetime(2026, 1, 9, 12, 0)),
        ], "Only Monday, Wednesday and Friday should have an attendance interval")

    def test_duration_based_centered_around_noon(self):
        """A duration-based (define amount of hours per day) attendance is centered around noon
        when the day is strictly inside the requested period."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Duration based 8h/day',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'duration_hours': 8})
                for day in range(5)
            ],
        })
        # dt_from/dt_to fall on the week-end so every week day is a "middle" day of the range
        result = self._times(
            calendar,
            datetime(2026, 1, 4, 0, 0, 0),  # Sunday
            datetime(2026, 1, 10, 23, 59, 59),  # Saturday
        )
        self.assertEqual(result, [
            (datetime(2026, 1, day, 8, 0), datetime(2026, 1, day, 16, 0))
            for day in range(5, 10)
        ], "8h duration should be centered around noon (08:00-16:00) on days strictly inside the period")

    def test_duration_based_front_loaded_on_boundary_day(self):
        """When the requested period cuts the noon-centered hours on its first (or last) day, the
        duration-based attendance is moved into the period, so that a narrow query at the edge of
        the day still returns the expected overlap. When it fits, it stays centered around noon."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Duration based 8h/day',
            'attendance_ids': [(5, 0, 0), (0, 0, {'dayofweek': '0', 'duration_hours': 8})],
        })
        # Querying only the last 2 hours of the day: without the front-loading logic, a
        # noon-centered 08:00-16:00 attendance would not overlap this window at all.
        result = self._times(calendar, datetime(2026, 1, 5, 21, 0, 0), datetime(2026, 1, 5, 23, 0, 0))
        self.assertEqual(result, [(datetime(2026, 1, 5, 21, 0), datetime(2026, 1, 5, 23, 0))],
            "Attendance should still be found when querying a narrow window at the end of the day")

        # Querying the early hours of the day: the attendance is moved back to fit the period.
        result = self._times(calendar, datetime(2026, 1, 5, 2, 0, 0), datetime(2026, 1, 5, 4, 0, 0))
        self.assertEqual(result, [(datetime(2026, 1, 5, 2, 0), datetime(2026, 1, 5, 4, 0))],
            "Attendance should still be found when querying a narrow window at the start of the day")

        # Querying the full day: the hours fit, they stay centered around noon.
        result_full_day = self._times(calendar, datetime(2026, 1, 5, 0, 0, 0), datetime(2026, 1, 5, 23, 59, 59))
        self.assertEqual(result_full_day, [(datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 16, 0))],
            "When the period does not cut them, the hours should stay centered around noon")

        # Querying from 10:00: the hours are moved after the start of the period, keeping their duration.
        result = self._times(calendar, datetime(2026, 1, 5, 10, 0, 0), datetime(2026, 1, 6, 23, 59, 59))
        self.assertEqual(result, [(datetime(2026, 1, 5, 10, 0), datetime(2026, 1, 5, 18, 0))],
            "On the first day, the hours should start at the period start when it is after the centered start")

    def test_duration_based_full_24h_coverage(self):
        """Multiple duration-based attendances summing up to 24h on a single day should cover the
        entire day, from time.min to time.max."""
        calendar = self.env['resource.calendar'].create({
            'name': '24h coverage',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': '0', 'duration_hours': 8}) for _ in range(3)
            ],
        })
        result = self._times(calendar, datetime(2026, 1, 5, 0, 0, 0), datetime(2026, 1, 5, 23, 59, 59))
        self.assertEqual(result, [
            (datetime(2026, 1, 5, 0, 0), datetime(2026, 1, 5, 8, 0)),
            (datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 16, 0)),
            (datetime(2026, 1, 5, 16, 0), datetime(2026, 1, 5, 23, 59, 59)),
        ], "3 x 8h duration-based attendances should cover the entire day without gaps")

    def test_domain_filter(self):
        """The optional domain should be applied to the fetched attendances before the intervals
        are computed, and the remaining attendance(s) recompute their placement without the
        filtered-out one."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Domain filter test',
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'dayofweek': '0', 'duration_hours': 2}),
                (0, 0, {'dayofweek': '0', 'duration_hours': 4}),
            ],
        })
        result = self._times(
            calendar,
            datetime(2026, 1, 5, 0, 0, 0),
            datetime(2026, 1, 5, 23, 59, 59),
            domain=[('duration_hours', '>', 3)],
        )
        self.assertEqual(result, [(datetime(2026, 1, 5, 10, 0), datetime(2026, 1, 5, 14, 0))],
            "Only the 4h attendance should remain, centered around noon on its own")

    def test_multiple_calendars_batched(self):
        """Calling _attendance_intervals on a recordset of several calendars should return one
        entry per calendar in the result dict."""
        full_time, part_time = self.env['resource.calendar'].create([{
            'name': '40h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour, 'hour_to': hour + 4})
                for day in range(5) for hour in (8, 13)
            ],
        }, {
            'name': 'Part time 12h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': 8, 'hour_to': 12})
                for day in (0, 2, 4)
            ],
        }])
        result = (full_time | part_time)._attendance_intervals(
            datetime.combine(self.monday, datetime.min.time()),
            datetime.combine(self.sunday, datetime.max.time()),
        )
        self.assertEqual(set(result.keys()), {full_time, part_time}, "One entry per calendar is expected")
        self.assertEqual(len(result[full_time]), 10, "40h/week calendar should have 10 intervals (2 per week day)")
        self.assertEqual(len(result[part_time]), 3, "Part time calendar should have 3 intervals (1 per working day)")

    def test_variable_calendar_only_considers_dated_attendances(self):
        """For a variable (dated) calendar, only attendances with a date (recurring or not) are
        considered; dayofweek-based attendances left over from a fixed schedule must be ignored."""
        calendar = self.env['resource.calendar'].create({
            'name': 'Variable calendar',
            'calendar_type': 'variable',
        })
        calendar.attendance_ids = [(0, 0, {
            'date': date(2026, 1, 5),
            'hour_from': 9,
            'hour_to': 17,
            'recurrency': True,
            'recurrency_type': 'weeks',
            'recurrency_interval': 1,
        })]
        result = self._times(
            calendar,
            datetime.combine(self.monday, datetime.min.time()),
            datetime.combine(self.sunday, datetime.max.time()),
        )
        self.assertEqual(result, [(datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 17, 0))],
            "Only the recurring dated attendance occurring within the period should be returned")

        # The recurrency should repeat the following week
        next_week_result = self._times(
            calendar,
            datetime(2026, 1, 12, 0, 0, 0),
            datetime(2026, 1, 18, 23, 59, 59),
        )
        self.assertEqual(next_week_result, [(datetime(2026, 1, 12, 9, 0), datetime(2026, 1, 12, 17, 0))],
            "The weekly recurrency should produce a new occurrence the following Monday")

    def test_clipping_to_query_range(self):
        """Attendance intervals must be clipped to fit inside [dt_from, dt_to], even when the
        underlying attendance starts/ends outside of that range."""
        calendar = self.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour, 'hour_to': hour + 4})
                for day in range(5) for hour in (8, 13)
            ],
        })
        # Cuts into the middle of the Monday morning slot and the Tuesday afternoon slot.
        result = self._times(calendar, datetime(2026, 1, 5, 10, 0, 0), datetime(2026, 1, 6, 15, 0, 0))
        self.assertEqual(result, [
            (datetime(2026, 1, 5, 10, 0), datetime(2026, 1, 5, 12, 0)),
            (datetime(2026, 1, 5, 13, 0), datetime(2026, 1, 5, 17, 0)),
            (datetime(2026, 1, 6, 8, 0), datetime(2026, 1, 6, 12, 0)),
            (datetime(2026, 1, 6, 13, 0), datetime(2026, 1, 6, 15, 0)),
        ], "Intervals should be clipped to dt_from/dt_to when they cut through an attendance")

    def test_no_attendance_returns_empty_intervals(self):
        """Querying a period with no matching attendance (e.g. a week-end only period on a
        Monday-to-Friday calendar) should return an empty set of intervals, not raise."""
        calendar = self.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour, 'hour_to': hour + 4})
                for day in range(5) for hour in (8, 13)
            ],
        })
        result = self._times(calendar, datetime(2026, 1, 3, 0, 0, 0), datetime(2026, 1, 4, 23, 59, 59))
        self.assertEqual(result, [], "No attendance should be found on a week-end only period")

    # ------------------------------------------------------------------
    # Flexible calendars (no attendance, only hours targets)
    # ------------------------------------------------------------------

    def _flexible_calendar(self, **vals):
        return self.env['resource.calendar'].create({'name': 'Flexible', 'calendar_type': 'undefined', **vals})

    def test_fully_flexible_returns_the_whole_period(self):
        """A fully flexible calendar (no hours target) works the whole period, availability or not."""
        calendar = self._flexible_calendar(hours_per_week=0, days_per_week=0)
        dt_from, dt_to = datetime(2026, 1, 7, 10, 0), datetime(2026, 1, 13, 18, 0)
        for availability in (False, True):
            with self.subTest(availability=availability):
                intervals = calendar._attendance_intervals(dt_from, dt_to, availability=availability)[calendar]
                self.assertEqual([(start, stop) for start, stop, _att in intervals], [(dt_from, dt_to)])
                attendance = intervals._items[0][2]
                self.assertEqual(attendance.calendar_id, calendar, "The made-up attendance belongs to the calendar")
                self.assertAlmostEqual(attendance.duration_hours, 152.0)

    def test_flexible_availability_returns_the_whole_period(self):
        """With availability, a flexible calendar with hours targets is available the whole period."""
        calendar = self._flexible_calendar(hours_per_week=40, days_per_week=5)
        dt_from, dt_to = datetime(2026, 1, 7, 0, 0), datetime(2026, 1, 13, 23, 59, 59)
        self.assertEqual(self._times(calendar, dt_from, dt_to, availability=True), [(dt_from, dt_to)])

    def test_flexible_week_starts_on_dt_from(self):
        """5 days/week, 8h/day queried from a Wednesday to the next Tuesday: the week starts on the
        Wednesday, so Wednesday to Sunday get 8h centered around noon and Monday/Tuesday nothing."""
        calendar = self._flexible_calendar(hours_per_week=40, days_per_week=5)
        self.assertAlmostEqual(calendar.hours_per_day, 8.0)
        result = self._times(calendar, datetime(2026, 1, 7, 0, 0), datetime(2026, 1, 13, 23, 59, 59))
        self.assertEqual(result, [
            (datetime(2026, 1, day, 8, 0), datetime(2026, 1, day, 16, 0))
            for day in range(7, 12)  # Wednesday 7th to Sunday 11th
        ])

    def test_flexible_weekly_hours_limit(self):
        """8h/day with 20h/week: 8h, 8h then the 4h left, then nothing until the next week."""
        calendar = self._flexible_calendar(hours_per_week=20, days_per_week=5, hours_per_day=8)
        result = self._times(calendar, datetime(2026, 1, 5, 0, 0), datetime(2026, 1, 12, 23, 59, 59))
        self.assertEqual(result, [
            (datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 16, 0)),
            (datetime(2026, 1, 6, 8, 0), datetime(2026, 1, 6, 16, 0)),
            (datetime(2026, 1, 7, 10, 0), datetime(2026, 1, 7, 14, 0)),
            # second week, starting on Monday 12th
            (datetime(2026, 1, 12, 8, 0), datetime(2026, 1, 12, 16, 0)),
        ])

    def test_flexible_boundary_days_like_duration_based(self):
        """On the first and last day, the hours are moved into the period when it cuts them, as for
        duration-based attendances: a 9PM-11PM query still gets 2 hours."""
        calendar = self._flexible_calendar(hours_per_week=40, days_per_week=5)
        self.assertEqual(
            self._times(calendar, datetime(2026, 1, 7, 21, 0), datetime(2026, 1, 7, 23, 0)),
            [(datetime(2026, 1, 7, 21, 0), datetime(2026, 1, 7, 23, 0))])
        self.assertEqual(
            self._times(calendar, datetime(2026, 1, 7, 10, 0), datetime(2026, 1, 8, 23, 59, 59)),
            [(datetime(2026, 1, 7, 10, 0), datetime(2026, 1, 7, 18, 0)),
             (datetime(2026, 1, 8, 8, 0), datetime(2026, 1, 8, 16, 0))])

    def test_flexible_domain_filters_made_up_attendances(self):
        """The domain applies to the made-up attendances too."""
        calendar = self._flexible_calendar(hours_per_week=20, days_per_week=5, hours_per_day=8)
        result = self._times(calendar, datetime(2026, 1, 5, 0, 0), datetime(2026, 1, 11, 23, 59, 59),
                             domain=[('duration_hours', '>', 5)])
        self.assertEqual(result, [
            (datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 16, 0)),
            (datetime(2026, 1, 6, 8, 0), datetime(2026, 1, 6, 16, 0)),
        ], "The 4h day is filtered out by the domain")

    def test_flexible_and_regular_calendars_batched(self):
        """Flexible and regular calendars can be computed in the same call."""
        regular = self.env['resource.calendar'].create({
            'name': 'Mondays 9-12',
            'attendance_ids': [(5, 0, 0), (0, 0, {'dayofweek': '0', 'hour_from': 9, 'hour_to': 12})],
        })
        flexible = self._flexible_calendar(hours_per_week=40, days_per_week=5)
        result = (regular | flexible)._attendance_intervals(datetime(2026, 1, 5, 0, 0), datetime(2026, 1, 5, 23, 59, 59))
        self.assertEqual([(s, e) for s, e, _att in result[regular]], [(datetime(2026, 1, 5, 9, 0), datetime(2026, 1, 5, 12, 0))])
        self.assertEqual([(s, e) for s, e, _att in result[flexible]], [(datetime(2026, 1, 5, 8, 0), datetime(2026, 1, 5, 16, 0))])
