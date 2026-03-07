# -*- coding: utf-8 -*-
import logging
from datetime import timedelta, datetime as dt

import pytz

from odoo import api, models

_logger = logging.getLogger(__name__)


class BiometricScheduleHelper(models.AbstractModel):
    """Helper for employee schedule lookups and worked-time calculations."""
    _name = 'biometric.schedule.helper'
    _description = 'Biometric Schedule Helper'

    @api.model
    def get_employee_tz(self, employee):
        """Return pytz timezone for an employee.

        Resolution: work calendar tz -> employee tz -> company calendar tz -> UTC
        """
        tz_name = (
                employee.resource_calendar_id.tz
                or employee.tz
                or employee.company_id.resource_calendar_id.tz
                or 'UTC'
        )
        return pytz.timezone(tz_name)

    @api.model
    def get_employee_day_schedule(self, employee, date, emp_tz):
        """Get scheduled start/end for an employee on a given date.

        Uses main_calendar_id -> calendar_group_ids -> resource.calendar.group.line.
        :return: dict with 'start', 'end' (tz-aware), 'break_hours' or None
        """
        calendar = employee.main_calendar_id
        if not calendar:
            return None
        calendar_groups = calendar.calendar_group_ids
        if not calendar_groups:
            return None

        day_of_week = str(date.weekday())
        lines = self.env['resource.calendar.group.line'].search([
            ('calendar_group_id', 'in', calendar_groups.ids),
            ('dayofweek', '=', day_of_week),
        ], order='hour_from asc')
        if not lines:
            return None

        work_lines = lines.filtered(lambda l: l.day_period != 'lunch')
        lunch_lines = lines.filtered(lambda l: l.day_period == 'lunch')
        if not work_lines:
            return None

        break_hours = sum(l.hour_to - l.hour_from for l in lunch_lines)
        hour_from = work_lines[0].hour_from
        hour_to = work_lines[-1].hour_to

        start_hour = int(hour_from)
        start_min = int((hour_from - start_hour) * 60)
        end_hour = int(hour_to)
        end_min = int((hour_to - end_hour) * 60)

        sched_start = emp_tz.localize(
            dt(date.year, date.month, date.day, start_hour, start_min))
        sched_end = emp_tz.localize(
            dt(date.year, date.month, date.day, end_hour, end_min))
        if sched_end <= sched_start:
            sched_end += timedelta(days=1)

        return {
            'start': sched_start,
            'end': sched_end,
            'break_hours': break_hours,
        }

    @api.model
    def is_scheduled_workday(self, employee, date):
        """Check if the employee is scheduled to work on the given date.

        :param employee: hr.employee record
        :param date: datetime.date object
        :return: True if the employee has work lines on that day
        """
        emp_tz = self.get_employee_tz(employee)
        schedule = self.get_employee_day_schedule(employee, date, emp_tz)
        return schedule is not None

    @api.model
    def detect_night_shift(self, employee):
        """Detect if an employee works night shift.

        Returns True if 70%+ of calendar lines have overnight patterns.
        """
        calendar = (
                employee.resource_calendar_id
                or employee.company_id.resource_calendar_id
        )
        if not calendar:
            return False
        schedules = self.env['resource.calendar.attendance'].search([
            ('calendar_id', '=', calendar.id),
            ('day_period', '!=', 'lunch'),
        ])
        if not schedules:
            return False
        night_patterns = sum(
            1 for s in schedules
            if s.hour_from > s.hour_to
            and s.hour_from >= 20.0
            and s.hour_to <= 10.0
        )
        total = len(schedules)
        if night_patterns > 0 and night_patterns >= (total * 0.7):
            _logger.info(
                "Employee %s: night shift detected (%d/%d)",
                employee.name, night_patterns, total)
            return True
        return False

    @api.model
    def calculate_worked_time(self, check_in, check_out, employee):
        """Calculate worked time considering schedule and grace periods.

        :param check_in: naive UTC datetime
        :param check_out: naive UTC datetime
        :param employee: hr.employee record
        :return: dict with 'worked_hours', 'late_minutes', 'early_leave_minutes'
        """
        emp_tz = self.get_employee_tz(employee)
        local_ci = pytz.utc.localize(check_in).astimezone(emp_tz)
        local_co = pytz.utc.localize(check_out).astimezone(emp_tz)
        work_date = local_ci.date()

        schedule = self.get_employee_day_schedule(
            employee, work_date, emp_tz)
        if not schedule:
            raw_hours = (check_out - check_in).total_seconds() / 3600.0
            return {
                'worked_hours': raw_hours,
                'late_minutes': 0.0,
                'early_leave_minutes': 0.0,
            }

        grace_minutes = 16
        sched_start = schedule['start']
        sched_end = schedule['end']
        break_hours = schedule.get('break_hours', 0.0)

        late_minutes = 0.0
        grace_start = sched_start + timedelta(minutes=grace_minutes)
        if local_ci > grace_start:
            late_minutes = int(round(
                (local_ci - sched_start).total_seconds() / 60.0))

        early_leave_minutes = 0.0
        grace_end = sched_end - timedelta(minutes=grace_minutes)
        if local_co < grace_end:
            early_leave_minutes = int(round(
                (sched_end - local_co).total_seconds() / 60.0))

        raw_hours = (check_out - check_in).total_seconds() / 3600.0
        worked_hours = max(0.0, raw_hours - break_hours)

        return {
            'worked_hours': worked_hours,
            'late_minutes': late_minutes,
            'early_leave_minutes': early_leave_minutes
        }

