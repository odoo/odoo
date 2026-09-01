# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import date, timedelta
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.hr_holidays.tests.common import TestHrHolidaysCommon


def _next_weekday(start, weekday):
    """ Return the first date on/after `start` whose date.weekday() is `weekday`. """
    d = start
    while d.weekday() != weekday:
        d += timedelta(days=1)
    return d


@tagged('post_install', '-at_install')
class TestLeaveOutsideSchedule(TestHrHolidaysCommon):
    """Encoding a time type outside an employee's working schedule (on
    the payrun time step):
    - working time entries count real duration and get a correct date_from, date_to instead of collapsing to 0.
    - absence entries outside the schedule are rejected with a notification instead of silently persisting.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # employee_emp has a real Mon-Fri 8-12/13-17 calendar, see common.py.
        cls.saturday = _next_weekday(date(2024, 1, 1), 5)

        cls.working_time_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Overtime (day)',
            'code': 'TESTOVERTIMEDAY',
            'count_as': 'working_time',
            'request_unit': 'day',
            'requires_allocation': False,
        })
        cls.working_time_type_hour = cls.env['hr.work.entry.type'].create({
            'name': 'Test Overtime (hour)',
            'code': 'TESTOVERTIMEHOUR',
            'count_as': 'working_time',
            'request_unit': 'hour',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
        })
        cls.absence_type = cls.env['hr.work.entry.type'].create({
            'name': 'Test Absence (day)',
            'code': 'TESTABSENCEDAY',
            'count_as': 'absence',
            'request_unit': 'day',
            'requires_allocation': False,
            'leave_validation_type': 'hr',
        })

    def test_working_time_day_unit_outside_schedule_counts_duration(self):
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.working_time_type.id,
            'request_date_from': self.saturday,
            'request_date_to': self.saturday,
        })
        self.assertEqual(leave.number_of_days, 1)
        self.assertEqual(leave.number_of_hours, self.hours_per_day)

    def test_absence_outside_schedule_dropped_with_multi_leave_request(self):
        with patch.object(self.env.registry['bus.bus'], '_sendone') as mock_send:
            leaves = self.env['hr.leave'].with_context(multi_leave_request=True).create([{
                'employee_id': self.employee_emp.id,
                'work_entry_type_id': self.absence_type.id,
                'request_date_from': self.saturday,
                'request_date_to': self.saturday,
            }])
            self.assertFalse(leaves.exists(), "the zero-duration absence should have been dropped")
            mock_send.assert_called_with(self.env.user, 'simple_notification', {
                'type': 'danger',
                'message': 'The time off is outside the working schedule of the employee',
            })

    def test_absence_outside_schedule_kept_without_multi_leave_request(self):
        leave = self.env['hr.leave'].with_context(leave_fast_create=True).create({
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.absence_type.id,
            'request_date_from': self.saturday,
            'request_date_to': self.saturday,
        })
        self.assertTrue(leave.exists())
        self.assertEqual(leave.number_of_days, 0)

    def test_hour_unit_working_time_explicit_hours_kept_as_is(self):
        leave = self.env['hr.leave'].create({
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.working_time_type_hour.id,
            'request_date_from': self.saturday,
            'request_date_to': self.saturday,
            'request_hour_from': 18,
            'request_hour_to': 22,
        })
        self.assertEqual(leave.request_hour_from, 18)
        self.assertEqual(leave.request_hour_to, 22)
        self.assertEqual(leave.number_of_hours, 4)

    def test_hour_unit_working_time_outside_schedule_no_validation_error_on_approve(self):
        leave = self.env['hr.leave'].with_context(tracking_disable=True).create({
            'employee_id': self.employee_emp.id,
            'work_entry_type_id': self.working_time_type_hour.id,
            'request_date_from': self.saturday,
            'request_date_to': self.saturday,
            'request_duration': 'full',
            'number_of_hours': 4,
        })
        self.assertEqual(leave.state, 'validate')
        self.assertEqual(leave.number_of_hours, 4)
        self.assertEqual((leave.date_to - leave.date_from).total_seconds() / 3600.0, 4)

    def test_get_hours_for_date_duration_based_calendar_outside_schedule(self):
        """ A calendar whose schedule is defined purely as durations (e.g.
        "8 hours/day", no fixed clock times) still returns a sensible hour
        range for a date outside the schedule, instead of the degenerate
        (0, 0) you'd get from reading meaningless hour_from/hour_to fields. """
        calendar = self.env['resource.calendar'].create({
            'name': 'Test Duration-based 40h/week',
            'company_id': self.company.id,
            'attendance_ids': [(0, 0, {'dayofweek': str(d), 'duration_hours': 8.0}) for d in range(5)],
        })
        employee = self.env['hr.employee'].create({
            'name': 'Test Duration Based Employee',
            'company_id': self.company.id,
            'resource_calendar_id': calendar.id,
        })
        hour_from, hour_to = employee._get_hours_for_date(self.saturday)
        self.assertEqual((hour_from, hour_to), (8.0, 16.0))

    def test_hour_unit_working_time_fully_flexible_centered_not_midnight(self):
        """ For a fully flexible employee, a full-duration hour-unit working
        time request is centered around noon rather than anchored at
        midnight (which would always render as a half-day gantt pill). """
        flexible_employee = self.env['hr.employee'].create({
            'name': 'Test Fully Flexible Employee',
            'company_id': self.company.id,
            'resource_calendar_id': False,
        })
        leave = self.env['hr.leave'].with_context(tracking_disable=True).create({
            'employee_id': flexible_employee.id,
            'work_entry_type_id': self.working_time_type_hour.id,
            'request_date_from': self.saturday,
            'request_date_to': self.saturday,
            'request_duration': 'full',
            'number_of_hours': 8,
        })
        self.assertEqual(leave.request_hour_from, 8.0)
        self.assertEqual(leave.request_hour_to, 16.0)

    def test_hour_unit_working_time_night_shift_crossing_midnight(self):
        """ A working time request whose hours roll over midnight into the
        next day (a night leave from 20:00 to 24:00) must get
        a correct date_to, not one derived from a stale request_date_to"""
        employee = self.env['hr.employee'].create({
            'name': 'Test Night Shift Employee',
            'company_id': self.company.id,
            'tz': 'Asia/Muscat',  # UTC + 4
        })
        leave = self.env['hr.leave'].create({
            'employee_id': employee.id,
            'work_entry_type_id': self.working_time_type_hour.id,
            'request_date_from': date(2025, 1, 6),
            'request_date_to': date(2025, 1, 6),
            'request_hour_from': 20,
            'request_hour_to': 24,
            'number_of_hours': 4,
        })
        self.assertEqual(leave.request_date_to, date(2025, 1, 7))
        self.assertEqual(leave.request_hour_to, 0.0)
        self.assertTrue(leave.date_from < leave.date_to, "date_to must not end up before date_from")
        self.assertEqual((leave.date_to - leave.date_from).total_seconds() / 3600.0, 4)
