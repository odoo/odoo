# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import time as timer
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from statistics import median
from zoneinfo import ZoneInfo

from odoo import Command
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger
from odoo.tools.intervals import Intervals

_logger = logging.getLogger(__name__)

TIMEZONES = ('Europe/Brussels', 'America/New_York', 'Asia/Kolkata', 'UTC')
ABSENCE_ATTENDANCE_DOMAIN = [('work_entry_type_id.count_as', '=', 'absence')]


@tagged('-standard', 'resource_benchmark', 'post_install', '-at_install')
class TestResourceIntervalsApiBenchmark(TransactionCase):
    """ Check that ``hr.employee._{attendance,leave,work}_intervals`` give the same intervals as
    ``resource.calendar._{attendance,leave,work}_intervals_batch``, with fewer queries and in
    less time, on many employees with versions on calendars of every kind.

    The ``_batch`` side is the cheapest correct use of that API:

    - regular calendars: one calendar-level call per (calendar, timezone), clipped to the
      version windows;
    - flexible calendars: one call per version window, as ``_batch`` reads the calendar of the
      resource at ``start_dt`` to place the flexible hours;
    - leaves: one call per (calendar, timezone) with the resources of that group.

    Own leaves are whole local days and every global leave has a company: ``_batch`` decides
    the flexible handling of own leaves on the current calendar of the resource and ignores
    the global leaves without company, while the new API follows the version windows.

    Not part of the standard test suite, run it with::

        odoo-bin -d <db> -i hr --test-tags resource_benchmark --stop-after-init
    """

    EMPLOYEES = 300
    LEAVES_PER_EMPLOYEE = 8
    PUBLIC_HOLIDAYS = 12
    RUNS = 3
    measures = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.year_start = date(2026, 1, 1)
        cls.other_company = cls.env['res.company'].create({'name': 'Benchmark other company'})
        cls.calendars = cls._create_calendars()
        cls.employees = cls._create_employees()
        cls._create_leaves()
        cls.has_absence_attendances = 'work_entry_type_id' in cls.env['resource.calendar.attendance']._fields

    @classmethod
    def _create_calendars(cls):
        def fixed(name, hours_by_day):
            return {'name': name, 'attendance_ids': [Command.clear()] + [
                Command.create({'dayofweek': str(day), 'hour_from': hour_from, 'hour_to': hour_to})
                for day, hours in hours_by_day.items() for hour_from, hour_to in hours
            ]}

        def flexible(name, hours_per_week, days_per_week):
            return {'name': name, 'calendar_type': 'undefined',
                    'hours_per_week': hours_per_week, 'days_per_week': days_per_week}

        week_days = range(5)
        calendars = cls.env['resource.calendar'].create([
            fixed('Full time', {day: [(8, 12), (13, 17)] for day in week_days}),
            fixed('Early full time', {day: [(6, 10), (10.5, 14.5)] for day in week_days}),
            fixed('Four days', {day: [(7, 12), (13, 18)] for day in range(4)}),
            fixed('Part time mornings', {day: [(9, 12)] for day in (0, 2, 4)}),
            fixed('Late shift', {day: [(14, 22)] for day in week_days}),
            fixed('Night end of day', {day: [(18, 24)] for day in week_days}),
            {'name': 'Duration based', 'attendance_ids': [Command.clear()] + [
                Command.create({'dayofweek': str(day), 'duration_hours': 7.6, 'duration_based': True})
                for day in week_days]},
            {'name': 'Duration based split', 'attendance_ids': [Command.clear()] + [
                Command.create({'dayofweek': str(day), 'duration_hours': hours, 'duration_based': True})
                for day in week_days for hours in (3, 4)]},
            flexible('Flexible 38h', 38, 5),
            flexible('Flexible 24h', 24, 3),
            flexible('Fully flexible', 0, 0),
        ])
        # dated attendances are only kept once the calendar is variable
        variable_calendars = cls.env['resource.calendar'].create([
            {'name': 'Variable weekly', 'calendar_type': 'variable'},
            {'name': 'Variable every other week', 'calendar_type': 'variable'},
        ])
        first_monday = date(2026, 1, 5)
        for calendar, recurrency_interval in zip(variable_calendars, (1, 2), strict=True):
            calendar.attendance_ids = [
                Command.create({
                    'date': first_monday + timedelta(days=day),
                    'hour_from': 9,
                    'hour_to': 17,
                    'recurrency': True,
                    'recurrency_type': 'weeks',
                    'recurrency_interval': recurrency_interval,
                })
                for day in (0, 1, 3)
            ]
        return calendars | variable_calendars

    @classmethod
    def _create_employees(cls):
        employees = cls.env['hr.employee'].create([{
            'name': f'Benchmark employee {i:04}',
            'tz': TIMEZONES[i % len(TIMEZONES)],
            'date_version': cls.year_start,
            'contract_date_start': cls.year_start,
            'resource_calendar_id': cls.calendars[i % len(cls.calendars)].id,
        } for i in range(cls.EMPLOYEES)])
        # a third keeps one version, the others change of calendar 2 or 5 times in the year
        for i, employee in enumerate(employees):
            versions = (1, 3, 6)[i % 3]
            for version in range(1, versions):
                employee.create_version({
                    'date_version': cls.year_start + timedelta(days=version * 365 // versions + i % 7),
                    'resource_calendar_id': cls.calendars[(i + version * 5) % len(cls.calendars)].id,
                })
        return employees

    @classmethod
    def _create_leaves(cls):
        leave_vals = []
        for i, employee in enumerate(cls.employees):
            zone = ZoneInfo(employee.tz)
            for n in range(cls.LEAVES_PER_EMPLOYEE):
                first_day = cls.year_start + timedelta(days=(i * 13 + n * 47) % 360)
                last_day = first_day + timedelta(days=n % 3)
                leave_vals.append({
                    'name': f'Leave {i}-{n}',
                    'resource_id': employee.resource_id.id,
                    'calendar_id': False,
                    'date_from': _naive_utc(datetime.combine(first_day, time.min, tzinfo=zone)),
                    'date_to': _naive_utc(datetime.combine(last_day, time(23, 59, 59), tzinfo=zone)),
                })
        for n in range(cls.PUBLIC_HOLIDAYS):
            day = cls.year_start + timedelta(days=15 + n * 29)
            is_other_company_holiday = n % 4 == 1
            is_calendar_holiday = n % 3 == 0 and not is_other_company_holiday
            leave_vals.append({
                'name': f'Public holiday {n}',
                'company_id': (cls.other_company if is_other_company_holiday else cls.env.company).id,
                'calendar_id': cls.calendars[n % len(cls.calendars)].id if is_calendar_holiday else False,
                'date_from': datetime.combine(day, time.min),
                'date_to': datetime.combine(day, time(23, 59, 59)),
            })
        cls.env['resource.calendar.leaves'].create(leave_vals)

    @classmethod
    def tearDownClass(cls):
        if cls.measures:
            _logger.info("Resource intervals API benchmark\n\n%s", cls._markdown_report())
        super().tearDownClass()

    @classmethod
    def _markdown_report(cls):
        versions = cls.env['hr.version'].search_count([('employee_id', 'in', cls.employees.ids)])
        lines = [(
            f"{len(cls.employees)} employees, {versions} versions, {len(cls.calendars)} calendars, "
            f"{len(TIMEZONES)} timezones, median of {cls.RUNS} runs with a cold cache.",
            "",
            "| Period | Method | `_batch` time | New time | Speedup | `_batch` queries | New queries |",
            "|---|---|---:|---:|---:|---:|---:|",
        )]
        for period, method, batch, new in cls.measures:
            speedup = batch['duration'] / new['duration'] if new['duration'] else float('inf')
            lines.append(
                f"| {period} | `{method}` | {batch['duration']:.3f} s | {new['duration']:.3f} s | x{speedup:.1f} "
                f"| {batch['queries']} | {new['queries']} |")
        return "\n".join(lines)

    def _measure(self, function):
        durations, query_counts, result = [], [], None
        for _run in range(self.RUNS):
            self.env.invalidate_all()
            queries_before = self.env.cr.sql_log_count
            start = timer.perf_counter()
            with mute_logger('odoo.addons.resource.models.resource_calendar'):  # _batch deprecation warnings
                result = function()
            durations.append(timer.perf_counter() - start)
            query_counts.append(self.env.cr.sql_log_count - queries_before)
        return result, {'duration': median(durations), 'queries': median(query_counts)}

    def _windows_by_employee(self, dt_from, dt_to):
        windows_by_resource = self.employees.resource_id._get_period_windows(dt_from, dt_to)
        return {employee: windows_by_resource.get(employee.resource_id, []) for employee in self.employees}

    def _batch_attendance_intervals(self, dt_from, dt_to, windows_by_employee, domain=None):
        no_resource = self.env['resource.resource']
        regular_groups = {
            (calendar, zone)
            for windows in windows_by_employee.values()
            for _start, _stop, calendar, zone in windows
            if not calendar._is_flexible()
        }
        intervals_by_group = {
            (calendar, zone): calendar._attendance_intervals_batch(dt_from, dt_to, {zone: no_resource}, domain)[False]
            for calendar, zone in regular_groups
        }
        no_attendance = self.env['resource.calendar.attendance']
        intervals_by_employee = {}
        for employee, windows in windows_by_employee.items():
            items = []
            for start, stop, calendar, zone in windows:
                if not calendar._is_flexible():
                    items.extend(intervals_by_group[calendar, zone] & Intervals([(start, stop, no_attendance)]))
                elif not domain:
                    resource = employee.resource_id
                    items.extend(calendar._attendance_intervals_batch(start, stop, {zone: resource})[resource.id])
            intervals_by_employee[employee] = Intervals(items, keep_distinct=True)
        return intervals_by_employee

    def _batch_leave_intervals(self, dt_from, dt_to, windows_by_employee):
        resources_by_group = defaultdict(lambda: self.env['resource.resource'])
        for employee, windows in windows_by_employee.items():
            for _start, _stop, calendar, zone in windows:
                resources_by_group[calendar, zone] |= employee.resource_id
        intervals_by_group = {
            (calendar, zone): calendar._leave_intervals_batch(dt_from, dt_to, {zone: resources})
            for (calendar, zone), resources in resources_by_group.items()
        }
        no_leave = self.env['resource.calendar.leaves']
        intervals_by_employee = {}
        for employee, windows in windows_by_employee.items():
            items = []
            for start, stop, calendar, zone in windows:
                group_intervals = intervals_by_group[calendar, zone][employee.resource_id.id]
                items.extend(group_intervals & Intervals([(start, stop, no_leave)]))
            intervals_by_employee[employee] = Intervals(items)
        return intervals_by_employee

    def _batch_work_intervals(self, dt_from, dt_to, windows_by_employee):
        attendances = self._batch_attendance_intervals(dt_from, dt_to, windows_by_employee)
        leaves = self._batch_leave_intervals(dt_from, dt_to, windows_by_employee)
        absences = self._batch_attendance_intervals(
            dt_from, dt_to, windows_by_employee, ABSENCE_ATTENDANCE_DOMAIN) if self.has_absence_attendances else {}
        return {
            employee: attendances[employee] - leaves[employee] - absences.get(employee, Intervals())
            for employee in self.employees
        }

    def _measure_signatures(self, function):
        intervals_by_employee, measure = self._measure(function)
        # before any other measure: its cache invalidation would reset the made-up attendances
        return {employee: _signature(intervals) for employee, intervals in intervals_by_employee.items()}, measure

    def _compare(self, period, dt_from, dt_to, method, batch_method, new_method):
        batch_signatures, batch_measure = self._measure_signatures(
            lambda: batch_method(dt_from, dt_to, self._windows_by_employee(dt_from, dt_to)))
        new_signatures, new_measure = self._measure_signatures(lambda: new_method(dt_from, dt_to))
        self.measures.append((period, method, batch_measure, new_measure))

        different_employees = self.employees.filtered(
            lambda employee: batch_signatures[employee] != new_signatures[employee])
        if different_employees:
            employee = different_employees[0]
            self.fail(
                f"{method} must give the same intervals as its _batch counterpart, {len(different_employees)} "
                f"employees differ, e.g. {employee.name}:\n_batch: {batch_signatures[employee]}\n"
                f"new:    {new_signatures[employee]}")
        self.assertLess(new_measure['queries'], batch_measure['queries'], f"{method} must run fewer queries")
        self.assertLess(new_measure['duration'], batch_measure['duration'], f"{method} must be faster")

    def _run_benchmark(self, period, dt_from, dt_to):
        employees = self.employees
        for method, batch_method, new_method in (
            ('_attendance_intervals', self._batch_attendance_intervals, employees._attendance_intervals),
            ('_leave_intervals', self._batch_leave_intervals, employees._leave_intervals),
            ('_work_intervals', self._batch_work_intervals, employees._work_intervals),
        ):
            with self.subTest(method=method):
                self._compare(period, dt_from, dt_to, method, batch_method, new_method)

    # The periods start on a Saturday at 06:00 UTC and end on a Sunday at 18:00 UTC: a week-end
    # day in every timezone of TIMEZONES, as duration-based hours are placed from the period
    # bound by the new API but around noon by _batch on the first and last day.

    def test_benchmark_one_month(self):
        # across the daylight saving time change of America/New_York (2026-03-08)
        self._run_benchmark('1 month', datetime(2026, 2, 28, 6, tzinfo=UTC), datetime(2026, 3, 29, 18, tzinfo=UTC))

    def test_benchmark_one_year(self):
        self._run_benchmark('1 year', datetime(2026, 1, 3, 6, tzinfo=UTC), datetime(2026, 12, 27, 18, tzinfo=UTC))


def _naive_utc(dt):
    return dt.astimezone(UTC).replace(tzinfo=None)


def _signature(intervals):
    """ Comparable form of intervals: UTC bounds to the second, saved payload ids and the hours
    of the unsaved attendances made up for flexible calendars.

    Flexible own leaves and 24:00 attendances end at 23:59:59.999999 but stored leaves at
    23:59:59: the sub-second rests depend on the flexibility of the calendar, which the two APIs
    take from different versions (see the class docstring), so they are left out. """
    signature = []
    for start, stop, records in intervals:
        start, stop = start.astimezone(UTC).replace(microsecond=0), stop.astimezone(UTC).replace(microsecond=0)
        if start == stop:
            continue
        saved_records = records.filtered('id')
        made_up_hours = sum((records - saved_records).mapped('duration_hours')) if records._name == 'resource.calendar.attendance' else 0
        signature.append((start, stop, tuple(sorted(saved_records.ids)), round(made_up_hours, 4)))
    return signature
