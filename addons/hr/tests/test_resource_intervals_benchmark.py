# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time as timer
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from statistics import median
from zoneinfo import ZoneInfo

from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.intervals import Intervals

_logger = logging.getLogger(__name__)


@tagged('-standard', 'resource_benchmark', 'post_install', '-at_install')
class TestResourceIntervalsBenchmark(TransactionCase):
    """Compare the resource-side interval methods (``hr.employee._attendance_intervals``,
    ``_leave_intervals``, ``_work_intervals``) with the calendar-side ``_batch`` methods used
    the way callers use them today: version periods grouped per (calendar, timezone), one
    ``_batch`` call per group, then clipped to each version period.

    Not part of the standard test suite, run it with::

        odoo-bin -d <db> -i hr --test-tags resource_benchmark --stop-after-init
    """

    EMPLOYEES = 400
    CALENDARS = 20
    VERSIONS_PER_EMPLOYEE = 3
    LEAVES_PER_EMPLOYEE = 6
    PUBLIC_HOLIDAYS = 12
    TIMEZONES = ('Europe/Brussels', 'America/New_York', 'Asia/Kolkata', 'UTC')
    RUNS = 3

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.year_start = date(2026, 1, 1)
        cls.year_end = date(2026, 12, 31)

        calendar_vals = []
        for i in range(cls.CALENDARS):
            if i % 10 == 7:
                # fully flexible: no hours target, the whole period is worked
                calendar_vals.append({'name': f'Benchmark calendar {i}', 'calendar_type': 'undefined',
                                      'hours_per_week': 0, 'days_per_week': 0})
                continue
            if i % 5 == 3:
                # flexible with hours targets: hours placed around noon until the weekly target
                hours_per_week, days_per_week = (38, 5) if i % 10 == 3 else (24, 3)
                calendar_vals.append({'name': f'Benchmark calendar {i}', 'calendar_type': 'undefined',
                                      'hours_per_week': hours_per_week, 'days_per_week': days_per_week})
                continue
            if i % 5 == 4:
                # duration-based calendars: no fixed hours, the hours are placed around noon
                attendances = [(0, 0, {'dayofweek': str(day), 'duration_hours': 6 + i % 3, 'duration_based': True})
                               for day in range(5)]
            else:
                start = 7 + i % 3
                days = range(5) if i % 2 else range(4)
                attendances = [(0, 0, {'dayofweek': str(day), 'hour_from': hour, 'hour_to': hour + 4})
                               for day in days for hour in (start, start + 5)]
            calendar_vals.append({'name': f'Benchmark calendar {i}', 'attendance_ids': [(5, 0, 0), *attendances]})
        cls.calendars = cls.env['resource.calendar'].create(calendar_vals)

        cls.employees = cls.env['hr.employee'].create([{
            'name': f'Benchmark employee {i}',
            'tz': cls.TIMEZONES[i % len(cls.TIMEZONES)],
            'date_version': cls.year_start,
            'contract_date_start': cls.year_start,
            'resource_calendar_id': cls.calendars[i % cls.CALENDARS].id,
        } for i in range(cls.EMPLOYEES)])
        # each employee changes of calendar a few times during the year
        step = 365 // cls.VERSIONS_PER_EMPLOYEE
        for i, employee in enumerate(cls.employees):
            for v in range(1, cls.VERSIONS_PER_EMPLOYEE):
                employee.create_version({
                    'date_version': cls.year_start + timedelta(days=v * step + i % 7),
                    'resource_calendar_id': cls.calendars[(i + v) % cls.CALENDARS].id,
                })

        cls.flexible_employees = cls.employees.filtered(
            lambda employee: any(version.resource_calendar_id._is_flexible() for version in employee.version_ids))

        leave_vals = []
        for i, employee in enumerate(cls.employees):
            for n in range(cls.LEAVES_PER_EMPLOYEE):
                day = cls.year_start + timedelta(days=(i * 13 + n * 53) % 360)
                leave_vals.append({
                    'name': f'Leave {i}-{n}',
                    'resource_id': employee.resource_id.id,
                    'calendar_id': False,
                    'date_from': datetime.combine(day, time(6)),
                    'date_to': datetime.combine(day + timedelta(days=n % 3), time(18)),
                })
        for n in range(cls.PUBLIC_HOLIDAYS):
            day = cls.year_start + timedelta(days=15 + n * 29)
            leave_vals.append({
                'name': f'Public holiday {n}',
                # some public holidays only apply to one calendar
                'calendar_id': cls.calendars[n].id if n % 3 == 0 else False,
                'date_from': datetime.combine(day, time.min),
                'date_to': datetime.combine(day, time(23, 59, 59)),
            })
        cls.env['resource.calendar.leaves'].create(leave_vals)

    # ------------------------------------------------------------------
    # Calendar-side (_batch) way, as done by the callers today
    # ------------------------------------------------------------------

    def _batch_intervals(self, employees, dt_from, dt_to, method):
        periods = employees.sudo()._get_version_periods(
            (dt_from - timedelta(days=1)).date(), (dt_to + timedelta(days=1)).date(),
            ['resource_calendar_id', 'tz'], check_contract=True)
        resources_per_group = defaultdict(lambda: self.env['resource.resource'])
        for employee, employee_periods in periods.items():
            for _date_from, _date_to, (calendar, tz) in employee_periods:
                resources_per_group[calendar, tz] |= employee.resource_id
        intervals_per_group = {
            (calendar, tz): getattr(calendar, method)(dt_from, dt_to, {ZoneInfo(tz): resources})
            for (calendar, tz), resources in resources_per_group.items()
        }
        result = {}
        no_attendance = self.env['resource.calendar.attendance']
        for employee in employees:
            items = []
            for date_from, date_to, (calendar, tz) in periods.get(employee, []):
                zone = ZoneInfo(tz)
                window = Intervals([(
                    max(dt_from, datetime.combine(date_from, time.min, tzinfo=zone)),
                    min(dt_to, datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=zone)),
                    no_attendance,
                )])
                items.extend(intervals_per_group[calendar, tz][employee.resource_id.id] & window)
            result[employee] = Intervals(items, keep_distinct=True)
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _measure(self, label, function):
        """Run ``function`` with a cold cache ``RUNS`` times, return its last result and log the
        median duration and query count."""
        durations, queries, result = [], [], None
        for _run in range(self.RUNS):
            self.env.invalidate_all()
            query_count = self.env.cr.sql_log_count
            start = timer.perf_counter()
            with mute_logger('odoo.addons.resource.models.resource_calendar'):  # deprecation warnings
                result = function()
            durations.append(timer.perf_counter() - start)
            queries.append(self.env.cr.sql_log_count - query_count)
        _logger.info("%-42s %8.3fs %7d queries", label, median(durations), median(queries))
        return result, median(durations)

    def _hours(self, intervals_per_employee):
        # durations computed in UTC: subtracting two datetimes of the same timezone gives the
        # wall-clock difference, one hour off for an interval spanning a DST change
        return {
            employee: round(sum(
                (stop.astimezone(UTC) - start.astimezone(UTC)).total_seconds() / 3600
                for start, stop, _meta in intervals
            ), 4)
            for employee, intervals in intervals_per_employee.items()
        }

    def _compare(self, label, dt_from, dt_to, batch_method, new_method):
        _logger.info("--- %s: %d employees, %s -> %s", label, len(self.employees), dt_from.date(), dt_to.date())
        old, old_duration = self._measure(f"{label} {batch_method}",
            lambda: self._batch_intervals(self.employees, dt_from, dt_to, batch_method))
        new, new_duration = self._measure(f"{label} {new_method}",
            lambda: getattr(self.employees, new_method)(dt_from, dt_to))
        _logger.info("%-42s x%.2f", f"{label} speedup", old_duration / new_duration if new_duration else 0)
        return self._hours(old), self._hours(new)

    # ------------------------------------------------------------------
    # Benchmarks
    # ------------------------------------------------------------------

    def _assert_same_hours(self, old_hours, new_hours, what):
        """Both ways must agree for the employees who never have a flexible calendar. For the
        others, the differences are only logged: the _batch way is wrong for flexible calendars,

        - it uses the calendar of the employee at the start of the request (not the version
          calendar of the period) to decide whether a resource is flexible,
        - its day loop skips the last day of the period when the request does not start at
          midnight (same bug as odoo/odoo#286054 on 19.0).
        """
        mismatches = {
            employee: (old_hours.get(employee), new_hours.get(employee))
            for employee in self.employees
            if old_hours.get(employee) != new_hours.get(employee)
        }
        flexible_mismatches = [employee for employee in mismatches if employee in self.flexible_employees]
        _logger.info("%-42s %d of %d employees with a flexible calendar differ (known _batch limitations)",
            f"{what} hours", len(flexible_mismatches), len(self.flexible_employees))
        self.assertFalse(
            {employee.name: hours for employee, hours in mismatches.items() if employee not in self.flexible_employees},
            f"Both methods should give the same {what} hours (old, new) for non-flexible calendars")

    def _run_benchmark(self, label, dt_from, dt_to):
        old_hours, new_hours = self._compare(label, dt_from, dt_to, '_attendance_intervals_batch', '_attendance_intervals')
        self._assert_same_hours(old_hours, new_hours, 'attendance')
        old_hours, new_hours = self._compare(label, dt_from, dt_to, '_work_intervals_batch', '_work_intervals')
        self._assert_same_hours(old_hours, new_hours, 'work')
        # leaves are only timed: the _batch way does not limit global leaves to the version periods
        self._compare(label, dt_from, dt_to, '_leave_intervals_batch', '_leave_intervals')

    # The periods start and end at noon UTC on a week-end day, which is a week-end day in every
    # timezone of TIMEZONES: on the first and last day of the period, the new calendar method
    # places duration-based hours from the period bound instead of around noon, on purpose.

    def test_benchmark_one_month(self):
        # Saturday 2026-02-28 -> Sunday 2026-03-29
        self._run_benchmark('month', datetime(2026, 2, 28, 12, tzinfo=UTC), datetime(2026, 3, 29, 12, tzinfo=UTC))

    def test_benchmark_one_year(self):
        # Saturday 2026-01-03 -> Sunday 2027-01-03
        self._run_benchmark('year', datetime(2026, 1, 3, 12, tzinfo=UTC), datetime(2027, 1, 3, 12, tzinfo=UTC))
