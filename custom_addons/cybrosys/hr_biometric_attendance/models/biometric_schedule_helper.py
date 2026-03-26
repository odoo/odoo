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

        work_lines = lines.filtered(lambda l: l.day_period != 'break')
        break_lines = lines.filtered(lambda l: l.day_period == 'break')
        if not work_lines:
            return None

        break_hours = sum(l.hour_to - l.hour_from for l in break_lines)
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
    def calculate_break_deduction(self, employee, work_date, local_ci, local_co, emp_tz):
        """Calculate total break hours to deduct.

        Break is only subtracted if the employee checked in before break start
        AND checked out after break end.

        :param employee: hr.employee record
        :param work_date: date used for break line lookup
        :param local_ci: localized check-in datetime
        :param local_co: localized check-out datetime
        :param emp_tz: pytz timezone
        :return: float break hours to deduct
        """
        break_deduction_hours = 0.0
        calendar = employee.main_calendar_id
        if not calendar:
            return break_deduction_hours

        calendar_groups = calendar.calendar_group_ids
        if not calendar_groups:
            return break_deduction_hours

        day_of_week = str(work_date.weekday())
        break_lines = self.env['resource.calendar.group.line'].search([
            ('calendar_group_id', 'in', calendar_groups.ids),
            ('dayofweek', '=', day_of_week),
            ('day_period', '=', 'break'),
        ])

        ref_date = local_ci.date() if hasattr(local_ci, 'date') else work_date
        for brk in break_lines:
            brk_hour = int(brk.hour_from)
            brk_min = int((brk.hour_from - brk_hour) * 60)
            brk_end_hour = int(brk.hour_to)
            brk_end_min = int((brk.hour_to - brk_end_hour) * 60)

            break_start = emp_tz.localize(
                dt(ref_date.year, ref_date.month, ref_date.day,
                   brk_hour, brk_min))
            break_end = emp_tz.localize(
                dt(ref_date.year, ref_date.month, ref_date.day,
                   brk_end_hour, brk_end_min))

            if local_ci < break_start and local_co > break_end:
                break_deduction_hours += (break_end - break_start).total_seconds() / 3600.0

        return break_deduction_hours

    @api.model
    def _break_overlap_minutes(self, employee, work_date, window_start,
                               window_end, emp_tz):
        """Calculate total break minutes that overlap with a time window.

        Used to exclude break time from late / early-leave calculations.

        :param employee: hr.employee record
        :param work_date: date for break-line lookup
        :param window_start: tz-aware datetime (window start)
        :param window_end: tz-aware datetime (window end)
        :param emp_tz: pytz timezone
        :return: float – overlap in minutes
        """
        overlap_minutes = 0.0
        calendar = employee.main_calendar_id
        if not calendar:
            return overlap_minutes
        calendar_groups = calendar.calendar_group_ids
        if not calendar_groups:
            return overlap_minutes

        day_of_week = str(work_date.weekday())
        break_lines = self.env['resource.calendar.group.line'].search([
            ('calendar_group_id', 'in', calendar_groups.ids),
            ('dayofweek', '=', day_of_week),
            ('day_period', '=', 'break'),
        ])

        ref_date = (window_start.date()
                    if hasattr(window_start, 'date') else work_date)
        for brk in break_lines:
            brk_hour = int(brk.hour_from)
            brk_min = int((brk.hour_from - brk_hour) * 60)
            brk_end_hour = int(brk.hour_to)
            brk_end_min = int((brk.hour_to - brk_end_hour) * 60)

            break_start = emp_tz.localize(
                dt(ref_date.year, ref_date.month, ref_date.day,
                   brk_hour, brk_min))
            break_end = emp_tz.localize(
                dt(ref_date.year, ref_date.month, ref_date.day,
                   brk_end_hour, brk_end_min))

            # Overlap = max(0, min(window_end, break_end) - max(window_start, break_start))
            overlap_start = max(window_start, break_start)
            overlap_end = min(window_end, break_end)
            if overlap_end > overlap_start:
                overlap_minutes += (
                    (overlap_end - overlap_start).total_seconds() / 60.0
                )

        return overlap_minutes

    @api.model
    def calculate_worked_time(self, check_in, check_out, employee):
        """Calculate worked time considering schedule and grace periods.

        Late and early-leave minutes exclude break time so that a break
        period between schedule-start and check-in (or between check-out
        and schedule-end) is not counted as a penalty.

        :param check_in: naive UTC datetime
        :param check_out: naive UTC datetime
        :param employee: hr.employee record
        :return: dict with 'worked_hours', 'late_minutes', 'early_leave_minutes',
                 'overtime_hours'
        """
        emp_tz = self.get_employee_tz(employee)
        local_ci = pytz.utc.localize(check_in).astimezone(emp_tz)
        local_co = pytz.utc.localize(check_out).astimezone(emp_tz)
        work_date = local_ci.date()

        schedule = self.get_employee_day_schedule(employee, work_date, emp_tz)
        if not schedule:
            raw_hours = (check_out - check_in).total_seconds() / 3600.0
            return {
                'worked_hours': raw_hours,
                'late_minutes': 0.0,
                'early_leave_minutes': 0.0,
                'overtime_hours': 0.0,
            }

        grace_minutes = 16
        sched_start = schedule['start']
        sched_end = schedule['end']
        grace_start = sched_start + timedelta(minutes=grace_minutes)
        grace_end = sched_end - timedelta(minutes=grace_minutes)

        # --- Late detection (excluding break time) ---
        late_minutes = 0.0
        if local_ci > grace_start:
            raw_late = (local_ci - sched_start).total_seconds() / 60.0
            break_in_late = self._break_overlap_minutes(
                employee, work_date, sched_start, local_ci, emp_tz)
            late_minutes = round(max(0.0, raw_late - break_in_late))

        # --- Early leave detection (excluding break time) ---
        early_leave_minutes = 0.0
        if local_co < grace_end:
            raw_early = (sched_end - local_co).total_seconds() / 60.0
            break_in_early = self._break_overlap_minutes(
                employee, work_date, local_co, sched_end, emp_tz)
            early_leave_minutes = round(max(0.0, raw_early - break_in_early))

        # --- Overtime: anything beyond the scheduled end ---
        overtime_hours = 0.0
        if local_co > sched_end:
            overtime_hours = (local_co - sched_end).total_seconds() / 3600.0

        # --- Worked hours: time present within schedule minus breaks ---
        effective_start = max(local_ci, sched_start)
        effective_end = min(local_co, sched_end)
        if effective_end > effective_start:
            raw_hours = (
                (effective_end - effective_start).total_seconds() / 3600.0
            )
            break_in_work = self._break_overlap_minutes(
                employee, work_date, effective_start, effective_end,
                emp_tz) / 60.0
            worked_hours = max(0.0, raw_hours - break_in_work)
        else:
            worked_hours = 0.0

        return {
            'worked_hours': worked_hours,
            'late_minutes': late_minutes,
            'early_leave_minutes': early_leave_minutes,
            'overtime_hours': overtime_hours,
        }



