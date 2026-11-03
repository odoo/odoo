# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, datetime, UTC

from odoo.tests.common import TransactionCase


class TestEmployeeAttendanceIntervals(TransactionCase):
    """Tests for hr.employee._attendance_intervals (inherited from resource.mixin), whose behavior
    is driven by hr.employee's override of _get_calendar_periods (calendar per hr.version)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.full_time_calendar = cls.env['resource.calendar'].create({
            'name': '40h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': hour, 'hour_to': hour + 4})
                for day in range(5) for hour in (8, 13)
            ],
        })
        cls.part_time_calendar = cls.env['resource.calendar'].create({
            'name': 'Part time 12h/week',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': 9, 'hour_to': 12})
                for day in (0, 2, 4)  # Monday, Wednesday, Friday
            ],
        })
        # Monday 2026-01-05 .. Sunday 2026-01-11
        cls.monday = datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC)
        cls.sunday = datetime(2026, 1, 11, 23, 59, 59, tzinfo=UTC)

    def _times(self, employee, dt_from, dt_to, **kwargs):
        intervals = employee._attendance_intervals(dt_from, dt_to, **kwargs)[employee]
        return [(start, stop) for start, stop, dummy_attendance in intervals]

    def test_full_time_employee(self):
        """A 40h/week employee should get the same intervals as its calendar directly, localized in its tz."""
        employee = self.env['hr.employee'].create({
            'name': 'Full time employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'resource_calendar_id': self.full_time_calendar.id,
        })
        result = self._times(employee, self.monday, self.sunday)
        self.assertEqual(result, [
            (datetime(2026, 1, day, hour, 0, tzinfo=UTC), datetime(2026, 1, day, hour + 4, 0, tzinfo=UTC))
            for day in range(5, 10) for hour in (8, 13)
        ], "A full time employee should have a morning and afternoon interval on each week day")

    def test_part_time_employee(self):
        """A part-timer working Monday/Wednesday/Friday mornings only should only get 3 intervals."""
        employee = self.env['hr.employee'].create({
            'name': 'Part time employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'resource_calendar_id': self.part_time_calendar.id,
        })
        result = self._times(employee, self.monday, self.sunday)
        self.assertEqual(result, [
            (datetime(2026, 1, 5, 9, 0, tzinfo=UTC), datetime(2026, 1, 5, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 7, 9, 0, tzinfo=UTC), datetime(2026, 1, 7, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 9, 9, 0, tzinfo=UTC), datetime(2026, 1, 9, 12, 0, tzinfo=UTC)),
        ], "Only Monday, Wednesday and Friday should have an attendance interval")

    def test_variable_schedule_employee(self):
        """An employee on a variable (dated) calendar should only get intervals for the dated
        occurrences, following the same rules as resource.calendar._attendance_intervals."""
        variable_calendar = self.env['resource.calendar'].create({
            'name': 'Variable calendar',
            'calendar_type': 'variable',
        })
        variable_calendar.attendance_ids = [(0, 0, {
            'date': date(2026, 1, 5),
            'hour_from': 9,
            'hour_to': 17,
            'recurrency': True,
            'recurrency_type': 'weeks',
            'recurrency_interval': 1,
        })]
        employee = self.env['hr.employee'].create({
            'name': 'Variable schedule employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'resource_calendar_id': variable_calendar.id,
        })
        result = self._times(employee, self.monday, self.sunday)
        self.assertEqual(result, [(datetime(2026, 1, 5, 9, 0, tzinfo=UTC), datetime(2026, 1, 5, 17, 0, tzinfo=UTC))],
            "Only the recurring dated attendance occurring within the period should be returned")

    def test_employee_without_contract_has_no_attendance(self):
        """An employee whose version has no contract_date_start should not have any attendance
        interval, as _get_calendar_periods only considers versions with contract overlap."""
        employee = self.env['hr.employee'].create({
            'name': 'No contract employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'resource_calendar_id': self.full_time_calendar.id,
        })
        result = self._times(employee, self.monday, self.sunday)
        self.assertEqual(result, [], "No attendance should be returned without a contract")

    def test_timezone_only_localizes_without_shifting_hours(self):
        """The calendar's naive hours represent wall-clock time in the employee's own timezone:
        changing the employee's tz must not shift the hours, only change the attached tzinfo."""
        employee = self.env['hr.employee'].create({
            'name': 'New York employee',
            'tz': 'America/New_York',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'resource_calendar_id': self.full_time_calendar.id,
        })
        result = employee._attendance_intervals(self.monday, self.sunday)[employee]
        start, stop, dummy_attendance = result._items[0]
        self.assertEqual((start.hour, start.minute), (8, 0), "Wall-clock hour must stay 8:00, not shift with the timezone")
        self.assertEqual(str(start.tzinfo), 'America/New_York')

    def test_domain_filter_is_forwarded(self):
        """The optional domain parameter must be forwarded down to the underlying calendar computation."""
        duration_based_calendar = self.env['resource.calendar'].create({
            'name': 'Duration based',
            'attendance_ids': [(5, 0, 0),
                (0, 0, {'dayofweek': '0', 'duration_hours': 2}),
                (0, 0, {'dayofweek': '0', 'duration_hours': 4}),
            ],
        })
        employee = self.env['hr.employee'].create({
            'name': 'Duration based employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'resource_calendar_id': duration_based_calendar.id,
        })
        result = self._times(
            employee,
            datetime(2026, 1, 5, 0, 0, 0, tzinfo=UTC),
            datetime(2026, 1, 5, 23, 59, 59, tzinfo=UTC),
            domain=[('duration_hours', '>', 3)],
        )
        self.assertEqual(result, [(datetime(2026, 1, 5, 10, 0, tzinfo=UTC), datetime(2026, 1, 5, 14, 0, tzinfo=UTC))],
            "Only the 4h attendance should remain once the 2h one is filtered out by the domain")

    def test_employee_spanning_two_versions_with_different_calendars(self):
        """When an employee changes calendar mid-period (new hr.version), _attendance_intervals
        must use each calendar exactly on its own version's date range, switching precisely on the
        version's date_version boundary."""
        # A daily (every week day) 9-12 calendar, distinct from self.part_time_calendar (which only
        # works Mon/Wed/Fri), so the switch is directly visible on the boundary day itself.
        second_calendar = self.env['resource.calendar'].create({
            'name': 'Every day mornings',
            'attendance_ids': [(5, 0, 0)] + [
                (0, 0, {'dayofweek': str(day), 'hour_from': 9, 'hour_to': 12})
                for day in range(5)
            ],
        })
        employee = self.env['hr.employee'].create({
            'name': 'Multi version employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'resource_calendar_id': self.full_time_calendar.id,
        })
        # New version starting Thursday 2026-01-08, same contract, different calendar.
        employee.create_version({
            'date_version': date(2026, 1, 8),
            'resource_calendar_id': second_calendar.id,
        })

        result = self._times(employee, self.monday, self.sunday)
        self.assertEqual(result, [
            # Monday, Tuesday, Wednesday: still on the full time calendar (version 1)
            (datetime(2026, 1, 5, 8, 0, tzinfo=UTC), datetime(2026, 1, 5, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 5, 13, 0, tzinfo=UTC), datetime(2026, 1, 5, 17, 0, tzinfo=UTC)),
            (datetime(2026, 1, 6, 8, 0, tzinfo=UTC), datetime(2026, 1, 6, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 6, 13, 0, tzinfo=UTC), datetime(2026, 1, 6, 17, 0, tzinfo=UTC)),
            (datetime(2026, 1, 7, 8, 0, tzinfo=UTC), datetime(2026, 1, 7, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 7, 13, 0, tzinfo=UTC), datetime(2026, 1, 7, 17, 0, tzinfo=UTC)),
            # Thursday, Friday: switched to the second calendar (version 2), mornings only
            (datetime(2026, 1, 8, 9, 0, tzinfo=UTC), datetime(2026, 1, 8, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 9, 9, 0, tzinfo=UTC), datetime(2026, 1, 9, 12, 0, tzinfo=UTC)),
        ], "The calendar switch should take effect exactly on the new version's date_version")

    def test_employee_spanning_two_versions_with_separate_contracts(self):
        """Same as above, but the 2 versions belong to 2 distinct contracts with a gap in between:
        the gap period must not produce any attendance interval."""
        employee = self.env['hr.employee'].create({
            'name': 'Two contracts employee',
            'tz': 'UTC',
            'date_version': date(2026, 1, 1),
            'contract_date_start': date(2026, 1, 1),
            'contract_date_end': date(2026, 1, 6),  # Contract 1 ends Tuesday
            'resource_calendar_id': self.full_time_calendar.id,
        })
        employee.create_version({
            'date_version': date(2026, 1, 9),
            'contract_date_start': date(2026, 1, 9),  # Contract 2 starts Friday: gap on Jan 7-8
            'resource_calendar_id': self.part_time_calendar.id,
        })

        result = self._times(employee, self.monday, self.sunday)
        self.assertEqual(result, [
            (datetime(2026, 1, 5, 8, 0, tzinfo=UTC), datetime(2026, 1, 5, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 5, 13, 0, tzinfo=UTC), datetime(2026, 1, 5, 17, 0, tzinfo=UTC)),
            (datetime(2026, 1, 6, 8, 0, tzinfo=UTC), datetime(2026, 1, 6, 12, 0, tzinfo=UTC)),
            (datetime(2026, 1, 6, 13, 0, tzinfo=UTC), datetime(2026, 1, 6, 17, 0, tzinfo=UTC)),
            (datetime(2026, 1, 9, 9, 0, tzinfo=UTC), datetime(2026, 1, 9, 12, 0, tzinfo=UTC)),
        ], "No attendance should be found during the gap between the two contracts (Jan 7-8)")
