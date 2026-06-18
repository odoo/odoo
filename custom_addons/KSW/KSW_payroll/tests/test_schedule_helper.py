# -*- coding: utf-8 -*-
"""Tests for biometric.schedule.helper (calculate_worked_time & friends).

These tests live in KSW_payroll because it depends on hr_biometric_attendance
(via KSW_attendance_leave) and KSW_working_schedule, so all required models
are available.

Schedule under test (set up once):
    Sun-Thu  08:00 - 16:30   work (full_day)
             12:00 - 12:30   break
    Fri/Sat  off

Asia/Riyadh = UTC+3, so 08:00 Riyadh = 05:00 UTC, 16:30 Riyadh = 13:30 UTC.
Grace period = 16 min (hardcoded in helper).
Scheduled work = 8.5h - 0.5h break = 8.0h = 480 min.
"""
from datetime import datetime as dt, date

from odoo.tests.common import TransactionCase


class TestScheduleHelper(TransactionCase):
    """Tests for biometric.schedule.helper.calculate_worked_time and helpers."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.helper = cls.env['biometric.schedule.helper']

        # ── Work schedule: Sun-Thu 08:00-16:30, break 12:00-12:30 ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Schedule Group',
        })
        work_days = ['0', '1', '2', '3', '6']  # Mon-Thu + Sun
        for day in work_days:
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })
            cls.env['resource.calendar.group.line'].create({
                'name': f'Break {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'break',
                'hour_from': 12.0,
                'hour_to': 12.5,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Helper Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Helper Employee',
            'resource_calendar_id': cls.calendar.id,
        })
        # main_calendar_id is what get_employee_day_schedule uses
        cls.employee.sudo().write({'main_calendar_id': cls.calendar.id})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _calc(self, check_in_utc, check_out_utc):
        """Shorthand for calculate_worked_time with our test employee."""
        return self.helper.calculate_worked_time(
            check_in_utc, check_out_utc, self.employee)

    # ==================================================================
    # Tests: get_employee_day_schedule
    # ==================================================================

    def test_schedule_returns_correct_start_end(self):
        """Schedule start/end should match work line hours."""
        emp_tz = self.helper.get_employee_tz(self.employee)
        sched = self.helper.get_employee_day_schedule(
            self.employee, date(2026, 3, 1), emp_tz)  # Sunday
        self.assertIsNotNone(sched)
        self.assertEqual(sched['start'].hour, 8)
        self.assertEqual(sched['start'].minute, 0)
        self.assertEqual(sched['end'].hour, 16)
        self.assertEqual(sched['end'].minute, 30)
        self.assertEqual(sched['break_hours'], 0.5)

    def test_schedule_none_on_weekend(self):
        """Friday has no work lines -> returns None."""
        emp_tz = self.helper.get_employee_tz(self.employee)
        sched = self.helper.get_employee_day_schedule(
            self.employee, date(2026, 3, 6), emp_tz)  # Friday
        self.assertIsNone(sched)

    def test_is_scheduled_workday_true(self):
        """Sunday is a workday."""
        self.assertTrue(
            self.helper.is_scheduled_workday(self.employee, date(2026, 3, 1)))

    def test_is_scheduled_workday_false(self):
        """Friday is NOT a workday."""
        self.assertFalse(
            self.helper.is_scheduled_workday(self.employee, date(2026, 3, 6)))

    # ==================================================================
    # Tests: On-time attendance (no issues)
    # ==================================================================

    def test_on_time_full_day(self):
        """Check-in at 08:00 and check-out at 16:30 -> no issues, 8h worked."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),    # 08:00 Riyadh
            dt(2026, 3, 1, 13, 30),   # 16:30 Riyadh
        )
        self.assertEqual(result['worked_hours'], 8.0)
        self.assertEqual(result['late_minutes'], 0.0)
        self.assertEqual(result['early_leave_minutes'], 0.0)
        self.assertEqual(result['overtime_hours'], 0.0)

    def test_within_grace_no_late(self):
        """Check-in at 08:15 (within 16-min grace) -> NOT late."""
        result = self._calc(
            dt(2026, 3, 1, 5, 15),    # 08:15 Riyadh
            dt(2026, 3, 1, 13, 30),
        )
        self.assertEqual(result['late_minutes'], 0.0)
        # Worked hours: 08:15 to 16:30 = 8.25h - 0.5h break = 7.75h
        self.assertEqual(result['worked_hours'], 7.75)

    def test_within_grace_no_early(self):
        """Check-out at 16:15 (within 16-min grace) -> NOT early."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),     # 08:00 Riyadh
            dt(2026, 3, 1, 13, 15),   # 16:15 Riyadh
        )
        self.assertEqual(result['early_leave_minutes'], 0.0)
        # Worked hours: 08:00 to 16:15 = 8.25h - 0.5h break = 7.75h
        self.assertEqual(result['worked_hours'], 7.75)

    # ==================================================================
    # Tests: Late arrival
    # ==================================================================

    def test_late_30_min(self):
        """Check-in at 08:30 -> 30 min late."""
        result = self._calc(
            dt(2026, 3, 1, 5, 30),    # 08:30 Riyadh
            dt(2026, 3, 1, 13, 30),
        )
        self.assertEqual(result['late_minutes'], 30.0)
        # Worked: 08:30-16:30 = 8h - 0.5h break = 7.5h
        self.assertEqual(result['worked_hours'], 7.5)

    def test_late_60_min(self):
        """Check-in at 09:00 -> 60 min late."""
        result = self._calc(
            dt(2026, 3, 1, 6, 0),     # 09:00 Riyadh
            dt(2026, 3, 1, 13, 30),
        )
        self.assertEqual(result['late_minutes'], 60.0)
        # Worked: 09:00-16:30 = 7.5h - 0.5h break = 7.0h
        self.assertEqual(result['worked_hours'], 7.0)

    def test_late_past_break_excludes_break(self):
        """Check-in at 13:00 Riyadh (after 12:00-12:30 break).

        Raw late = 13:00 - 08:00 = 300 min, but break (30 min) is between
        sched_start and check-in, so late = 300 - 30 = 270 min.
        """
        result = self._calc(
            dt(2026, 3, 1, 10, 0),    # 13:00 Riyadh
            dt(2026, 3, 1, 13, 30),   # 16:30 Riyadh
        )
        self.assertEqual(result['late_minutes'], 270.0)
        # Worked: 13:00-16:30 = 3.5h, no break overlap -> 3.5h
        self.assertEqual(result['worked_hours'], 3.5)

    def test_late_at_exactly_grace_boundary(self):
        """Check-in at 08:17 (1 min past 16-min grace) -> late = 17 min."""
        result = self._calc(
            dt(2026, 3, 1, 5, 17),    # 08:17 Riyadh
            dt(2026, 3, 1, 13, 30),
        )
        self.assertEqual(result['late_minutes'], 17.0)

    # ==================================================================
    # Tests: Early leave
    # ==================================================================

    def test_early_leave_30_min(self):
        """Check-out at 16:00 Riyadh (= 13:00 UTC) -> 30 min early."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),     # 08:00 Riyadh
            dt(2026, 3, 1, 13, 0),    # 16:00 Riyadh
        )
        self.assertEqual(result['early_leave_minutes'], 30.0)
        # Worked: 08:00-16:00 = 8h - 0.5h break = 7.5h
        self.assertEqual(result['worked_hours'], 7.5)

    def test_early_leave_before_break_excludes_break(self):
        """Check-out at 11:00 Riyadh (= 08:00 UTC), before 12:00-12:30 break.

        Raw early = 16:30 - 11:00 = 330 min, break (30 min) falls in
        [11:00, 16:30], so early = 330 - 30 = 300 min.
        """
        result = self._calc(
            dt(2026, 3, 1, 5, 0),     # 08:00 Riyadh
            dt(2026, 3, 1, 8, 0),     # 11:00 Riyadh
        )
        self.assertEqual(result['early_leave_minutes'], 300.0)
        # Worked: 08:00-11:00 = 3h, no break overlap -> 3.0h
        self.assertEqual(result['worked_hours'], 3.0)

    def test_early_leave_at_grace_boundary(self):
        """Check-out at 16:13 Riyadh (= 13:13 UTC), 1 min past grace -> early = 17 min."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),     # 08:00 Riyadh
            dt(2026, 3, 1, 13, 13),   # 16:13 Riyadh
        )
        self.assertEqual(result['early_leave_minutes'], 17.0)

    # ==================================================================
    # Tests: Late AND early combined
    # ==================================================================

    def test_late_and_early(self):
        """Check-in at 09:00 Riyadh, check-out at 15:00 Riyadh.

        late = 60 min (09:00 - 08:00, no break in that window)
        early = 16:30 - 15:00 = 90 min (no break in that window)
        """
        result = self._calc(
            dt(2026, 3, 1, 6, 0),     # 09:00 Riyadh
            dt(2026, 3, 1, 12, 0),    # 15:00 Riyadh
        )
        self.assertEqual(result['late_minutes'], 60.0)
        self.assertEqual(result['early_leave_minutes'], 90.0)
        # Worked: 09:00-15:00 = 6h - 0.5h break = 5.5h
        self.assertEqual(result['worked_hours'], 5.5)

    # ==================================================================
    # Tests: Overtime
    # ==================================================================

    def test_overtime_1_hour(self):
        """Check-out at 17:30 Riyadh (= 14:30 UTC) -> 1h overtime."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),     # 08:00 Riyadh
            dt(2026, 3, 1, 14, 30),   # 17:30 Riyadh
        )
        self.assertEqual(result['early_leave_minutes'], 0.0)
        self.assertEqual(result['overtime_hours'], 1.0)
        # Worked: capped at schedule window 08:00-16:30 = 8.5h - 0.5h break = 8.0h
        self.assertEqual(result['worked_hours'], 8.0)

    def test_overtime_2_hours(self):
        """Check-out at 18:30 Riyadh (= 15:30 UTC) -> 2h overtime."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),     # 08:00 Riyadh
            dt(2026, 3, 1, 15, 30),   # 18:30 Riyadh
        )
        self.assertEqual(result['overtime_hours'], 2.0)
        self.assertEqual(result['worked_hours'], 8.0)

    # ==================================================================
    # Tests: No-checkout scenario (check_in == check_out)
    # ==================================================================

    def test_no_checkout_within_grace(self):
        """CI=CO at 08:10 (within grace): late=0, early=entire day minus break.

        early_raw = 16:30 - 08:10 = 500 min
        break overlap in [08:10, 16:30] with [12:00, 12:30] = 30 min
        early = 500 - 30 = 470 min
        """
        result = self._calc(
            dt(2026, 3, 1, 5, 10),    # 08:10 Riyadh
            dt(2026, 3, 1, 5, 10),    # same
        )
        self.assertEqual(result['late_minutes'], 0.0)
        self.assertEqual(result['early_leave_minutes'], 470.0)
        self.assertEqual(result['worked_hours'], 0.0)

    def test_no_checkout_after_grace(self):
        """CI=CO at 08:30 (past grace): late=30, early=entire day minus break.

        late = 30 min (08:30 - 08:00, no break in that window)
        early_raw = 16:30 - 08:30 = 480 min
        break overlap in [08:30, 16:30] with [12:00, 12:30] = 30 min
        early = 480 - 30 = 450 min
        """
        result = self._calc(
            dt(2026, 3, 1, 5, 30),    # 08:30 Riyadh
            dt(2026, 3, 1, 5, 30),    # same
        )
        self.assertEqual(result['late_minutes'], 30.0)
        self.assertEqual(result['early_leave_minutes'], 450.0)
        self.assertEqual(result['worked_hours'], 0.0)

    # ==================================================================
    # Tests: No schedule (unscheduled day / no calendar)
    # ==================================================================

    def test_no_schedule_raw_hours(self):
        """Employee without main_calendar_id -> raw hours, no penalties."""
        emp_no_cal = self.env['hr.employee'].create({
            'name': 'No Calendar Employee',
        })
        # Ensure main_calendar_id is empty
        emp_no_cal.sudo().write({'main_calendar_id': False})
        result = self.helper.calculate_worked_time(
            dt(2026, 3, 1, 5, 0),
            dt(2026, 3, 1, 13, 0),
            emp_no_cal,
        )
        # No schedule -> raw diff = 8h
        self.assertEqual(result['worked_hours'], 8.0)
        self.assertEqual(result['late_minutes'], 0.0)
        self.assertEqual(result['early_leave_minutes'], 0.0)
        self.assertEqual(result['overtime_hours'], 0.0)

    # ==================================================================
    # Tests: _break_overlap_minutes
    # ==================================================================

    def test_break_overlap_full(self):
        """Window fully contains break -> overlap = 30 min."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        ref_date = date(2026, 3, 1)  # Sunday
        window_start = emp_tz.localize(dt(2026, 3, 1, 8, 0))
        window_end = emp_tz.localize(dt(2026, 3, 1, 16, 30))
        overlap = self.helper._break_overlap_minutes(
            self.employee, ref_date, window_start, window_end, emp_tz)
        self.assertEqual(overlap, 30.0)

    def test_break_overlap_partial_start(self):
        """Window starts inside break -> partial overlap."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        ref_date = date(2026, 3, 1)
        window_start = emp_tz.localize(dt(2026, 3, 1, 12, 15))
        window_end = emp_tz.localize(dt(2026, 3, 1, 16, 30))
        overlap = self.helper._break_overlap_minutes(
            self.employee, ref_date, window_start, window_end, emp_tz)
        self.assertEqual(overlap, 15.0)

    def test_break_overlap_partial_end(self):
        """Window ends inside break -> partial overlap."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        ref_date = date(2026, 3, 1)
        window_start = emp_tz.localize(dt(2026, 3, 1, 8, 0))
        window_end = emp_tz.localize(dt(2026, 3, 1, 12, 15))
        overlap = self.helper._break_overlap_minutes(
            self.employee, ref_date, window_start, window_end, emp_tz)
        self.assertEqual(overlap, 15.0)

    def test_break_overlap_none(self):
        """Window before break -> no overlap."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        ref_date = date(2026, 3, 1)
        window_start = emp_tz.localize(dt(2026, 3, 1, 8, 0))
        window_end = emp_tz.localize(dt(2026, 3, 1, 11, 0))
        overlap = self.helper._break_overlap_minutes(
            self.employee, ref_date, window_start, window_end, emp_tz)
        self.assertEqual(overlap, 0.0)

    def test_break_overlap_after_break(self):
        """Window entirely after break -> no overlap."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        ref_date = date(2026, 3, 1)
        window_start = emp_tz.localize(dt(2026, 3, 1, 13, 0))
        window_end = emp_tz.localize(dt(2026, 3, 1, 16, 30))
        overlap = self.helper._break_overlap_minutes(
            self.employee, ref_date, window_start, window_end, emp_tz)
        self.assertEqual(overlap, 0.0)

    def test_break_overlap_on_friday(self):
        """Friday has no work/break lines -> overlap = 0."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        ref_date = date(2026, 3, 6)  # Friday
        window_start = emp_tz.localize(dt(2026, 3, 6, 8, 0))
        window_end = emp_tz.localize(dt(2026, 3, 6, 16, 30))
        overlap = self.helper._break_overlap_minutes(
            self.employee, ref_date, window_start, window_end, emp_tz)
        self.assertEqual(overlap, 0.0)

    # ==================================================================
    # Tests: calculate_break_deduction
    # ==================================================================

    def test_break_deduction_full_day(self):
        """CI before break, CO after break -> deduct full 0.5h."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        local_ci = emp_tz.localize(dt(2026, 3, 1, 8, 0))
        local_co = emp_tz.localize(dt(2026, 3, 1, 16, 30))
        deduction = self.helper.calculate_break_deduction(
            self.employee, date(2026, 3, 1), local_ci, local_co, emp_tz)
        self.assertEqual(deduction, 0.5)

    def test_break_deduction_ci_after_break(self):
        """CI after break end -> no break deduction."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        local_ci = emp_tz.localize(dt(2026, 3, 1, 13, 0))
        local_co = emp_tz.localize(dt(2026, 3, 1, 16, 30))
        deduction = self.helper.calculate_break_deduction(
            self.employee, date(2026, 3, 1), local_ci, local_co, emp_tz)
        self.assertEqual(deduction, 0.0)

    def test_break_deduction_co_before_break(self):
        """CO before break start -> no break deduction."""
        import pytz
        emp_tz = pytz.timezone('Asia/Riyadh')
        local_ci = emp_tz.localize(dt(2026, 3, 1, 8, 0))
        local_co = emp_tz.localize(dt(2026, 3, 1, 11, 30))
        deduction = self.helper.calculate_break_deduction(
            self.employee, date(2026, 3, 1), local_ci, local_co, emp_tz)
        self.assertEqual(deduction, 0.0)

    # ==================================================================
    # Tests: Consistency – late + early + worked = scheduled hours
    # ==================================================================

    def test_consistency_late_early_worked_sum(self):
        """late/60 + early/60 + worked ≈ scheduled hours (8.0h).

        Check-in 09:00 (late 60), check-out 15:00 (early 90).
        60/60 + 90/60 + 5.5 = 1.0 + 1.5 + 5.5 = 8.0
        """
        result = self._calc(
            dt(2026, 3, 1, 6, 0),     # 09:00 Riyadh (60 min late)
            dt(2026, 3, 1, 12, 0),    # 15:00 Riyadh (90 min early)
        )
        total = (result['late_minutes'] / 60.0
                 + result['early_leave_minutes'] / 60.0
                 + result['worked_hours'])
        self.assertEqual(total, 8.0,
                         "late + early + worked should sum to scheduled hours")

    def test_consistency_no_issue(self):
        """On-time full day: worked = 8.0h, everything else = 0."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),
            dt(2026, 3, 1, 13, 30),
        )
        total = (result['late_minutes'] / 60.0
                 + result['early_leave_minutes'] / 60.0
                 + result['worked_hours'])
        self.assertEqual(total, 8.0)

    # ==================================================================
    # Tests: Different days of the week
    # ==================================================================

    def test_monday_workday(self):
        """Monday is a scheduled workday."""
        result = self._calc(
            dt(2026, 3, 2, 5, 0),     # Monday 08:00 Riyadh
            dt(2026, 3, 2, 13, 30),   # 16:30 Riyadh
        )
        self.assertEqual(result['worked_hours'], 8.0)

    def test_friday_no_schedule(self):
        """Friday -> no schedule -> raw hours, no penalties."""
        result = self._calc(
            dt(2026, 3, 6, 5, 0),     # Friday 08:00 Riyadh
            dt(2026, 3, 6, 13, 30),   # 16:30 Riyadh
        )
        # No schedule -> raw diff = 8.5h
        self.assertEqual(result['worked_hours'], 8.5)

    # ==================================================================
    # Tests: Edge – check-in before / check-out after schedule
    # ==================================================================

    def test_checkin_before_schedule(self):
        """CI at 07:30 (before 08:00) -> not late, worked capped to schedule."""
        result = self._calc(
            dt(2026, 3, 1, 4, 30),    # 07:30 Riyadh
            dt(2026, 3, 1, 13, 30),   # 16:30 Riyadh
        )
        self.assertEqual(result['late_minutes'], 0.0)
        # Worked capped: effective_start = max(07:30, 08:00) = 08:00
        # 08:00-16:30 = 8.5h - 0.5h break = 8.0h
        self.assertEqual(result['worked_hours'], 8.0)

    def test_checkout_after_schedule(self):
        """CO at 18:00 Riyadh (= 15:00 UTC) -> overtime 1.5h, worked capped."""
        result = self._calc(
            dt(2026, 3, 1, 5, 0),     # 08:00 Riyadh
            dt(2026, 3, 1, 15, 0),    # 18:00 Riyadh
        )
        self.assertEqual(result['early_leave_minutes'], 0.0)
        self.assertEqual(result['overtime_hours'], 1.5)
        self.assertEqual(result['worked_hours'], 8.0)
