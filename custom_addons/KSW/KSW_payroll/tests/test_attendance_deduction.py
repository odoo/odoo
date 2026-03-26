# -*- coding: utf-8 -*-
"""Tests for KSW Payroll attendance deduction fields on hr.attendance.

Deduction rules (hardcoded):
    All employees: 30 days/month, 8 hours/day = 480 min/day.
    Deduction = (deductible_minutes / 480) * daily_rate, capped at daily_rate.

Contract:
    wage=6000  da=0  travel=500  meal=300  medical=200  other=0  hra=1500
    Deductible base = 6000+500+300+200 = 7000  (HRA excluded)
    Daily rate = 7000 / 30 = 233.333...
"""
from datetime import datetime as dt, date

from odoo.tests.common import TransactionCase


class TestAttendanceDeduction(TransactionCase):
    """Tests for the KSW Payroll attendance deduction fields on hr.attendance."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule (still needed for employee, but NOT used in deduction) ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Payroll Group',
        })
        work_days = ['0', '1', '2', '3', '6']  # Mon-Thu + Sun
        for day in work_days:
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work Day {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })
            cls.env['resource.calendar.group.line'].create({
                'name': f'Break Day {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'break',
                'hour_from': 12.0,
                'hour_to': 13.0,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Payroll Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Payroll Employee',
            'resource_calendar_id': cls.calendar.id,
        })

        # Update the auto-created version with our test values
        # (Odoo auto-creates a version on employee create; we reuse it)
        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Test Version 2026',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': cls.calendar.id,
            'wage': 6000.0,
            'da': 0.0,
            'travel_allowance': 500.0,
            'meal_allowance': 300.0,
            'medical_allowance': 200.0,
            'other_allowance': 0.0,
            'hra': 1500.0,  # housing — excluded from deduction base
        })

        # Force current_version_id recomputation
        cls.employee._compute_current_version_id()

        # Expected values
        # Deductible base = 6000 + 0 + 500 + 300 + 200 + 0 = 7000
        # Daily rate = 7000 / 30 = 233.333...
        # Scheduled minutes = hardcoded 480 (8 hours)
        cls.expected_base = 7000.0
        cls.expected_daily_rate = 7000.0 / 30.0
        cls.expected_scheduled_minutes = 480.0  # hardcoded 8h

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_attendance(self, check_in, check_out=None, **kwargs):
        """Create an hr.attendance record with optional overrides."""
        vals = {
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out,
        }
        vals.update(kwargs)
        return self.env['hr.attendance'].create(vals)

    # ==================================================================
    # BASIC DEDUCTION COMPUTATION
    # ==================================================================

    def test_no_issue_no_deduction(self):
        """Clean attendance record -> deduction = 0."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),   # UTC -> 08:00 Riyadh (Sun)
            check_out=dt(2026, 3, 1, 13, 30), # UTC -> 16:30 Riyadh
        )
        self.assertEqual(att.x_deduction_amount, 0.0)
        self.assertAlmostEqual(att.x_deductible_base, self.expected_base, places=2)
        self.assertAlmostEqual(att.x_daily_rate, self.expected_daily_rate, places=2)

    def test_deductible_base_excludes_hra(self):
        """Housing allowance (HRA) must NOT be in the deductible base."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
        )
        self.assertAlmostEqual(att.x_deductible_base, 7000.0, places=2,
                               msg="HRA (1500) must be excluded from deductible base.")

    def test_daily_rate_is_base_div_30(self):
        """Daily rate = deductible base / 30."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
        )
        self.assertAlmostEqual(att.x_daily_rate, 7000.0 / 30.0, places=2)

    def test_deductible_base_includes_all_allowances(self):
        """Every allowance except HRA is part of the deductible base."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
        )
        # wage 6000 + da 0 + travel 500 + meal 300 + medical 200 + other 0 = 7000
        self.assertAlmostEqual(att.x_deductible_base, 7000.0, places=2)

    # ==================================================================
    # ABSENCE DEDUCTION
    # ==================================================================

    def test_full_day_absence_deduction(self):
        """An absent day should deduct one full daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 5, 0),
            x_is_absent=True,
        )
        self.assertTrue(att.x_net_is_absent)
        self.assertAlmostEqual(att.x_deduction_amount, self.expected_daily_rate, places=2,
                               msg="Absent day deduction should equal one daily rate.")

    def test_absent_deduction_equals_daily_rate_exactly(self):
        """Verify absent deduction is exactly daily_rate, not more, not less."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 2, 5, 0),   # Monday
            check_out=dt(2026, 3, 2, 5, 0),
            x_is_absent=True,
        )
        self.assertAlmostEqual(att.x_deduction_amount, 7000.0 / 30.0, places=2)

    # ==================================================================
    # LATE MINUTES DEDUCTION
    # ==================================================================

    def test_late_minutes_deduction(self):
        """Late 30 min -> deduction = (30/480) * daily_rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=30.0,
        )
        expected = (30.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    def test_late_minutes_different_values(self):
        """Late 90 min -> deduction = (90/480) * daily_rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 6, 30),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=90.0,
        )
        expected = (90.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    def test_late_1_minute(self):
        """Late 1 min -> very small deduction."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 1),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=1.0,
        )
        expected = (1.0 / 480.0) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    def test_late_half_day(self):
        """Late 240 min (half of 480) -> deduction = 50% of daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=240.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate / 2.0, places=2)

    # ==================================================================
    # EARLY LEAVE DEDUCTION
    # ==================================================================

    def test_early_leave_deduction(self):
        """Left 60 min early -> deduction = (60/480) * daily_rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 12, 30),
            x_early_leave_minutes=60.0,
        )
        expected = (60.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    def test_early_leave_15_min(self):
        """Left 15 min early -> small deduction."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 15),
            x_early_leave_minutes=15.0,
        )
        expected = (15.0 / 480.0) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    # ==================================================================
    # COMBINED LATE + EARLY
    # ==================================================================

    def test_late_and_early_combined(self):
        """Late 20 + early 40 = 60 total deductible minutes."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 20),
            check_out=dt(2026, 3, 1, 12, 50),
            x_late_minutes=20.0,
            x_early_leave_minutes=40.0,
        )
        expected = (60.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    def test_late_and_early_equal_parts(self):
        """Late 100 + early 100 = 200 total minutes."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=100.0,
            x_early_leave_minutes=100.0,
        )
        expected = (200.0 / 480.0) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    # ==================================================================
    # DEDUCTION CAP (never exceeds daily rate)
    # ==================================================================

    def test_deduction_capped_at_daily_rate(self):
        """Early leave exceeding 480 min must not exceed daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 10),
            check_out=dt(2026, 3, 1, 5, 10),
            x_early_leave_minutes=499.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate, places=2,
            msg="Deduction must be capped at the daily rate.",
        )

    def test_deduction_cap_with_late_and_early(self):
        """Combined late + early exceeding 480 min must be capped."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 10),
            check_out=dt(2026, 3, 1, 5, 10),
            x_late_minutes=200.0,
            x_early_leave_minutes=300.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate, places=2,
            msg="Combined late+early deduction must not exceed daily rate.",
        )

    def test_deduction_cap_exactly_at_limit(self):
        """Deductible minutes = 480 -> deduction = daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_early_leave_minutes=480.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate, places=2,
        )

    def test_deduction_cap_slightly_over(self):
        """Deductible minutes = 481 -> capped at daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=481.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate, places=2,
        )

    def test_deduction_just_under_cap(self):
        """Deductible minutes = 479 -> just under daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=479.0,
        )
        expected = (479.0 / 480.0) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
        self.assertLess(att.x_deduction_amount, self.expected_daily_rate)

    def test_deduction_cap_large_overshoot(self):
        """Extreme case: 900 min late -> still capped."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=900.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate, places=2,
        )

    # ==================================================================
    # ABSENT OVERRIDES PARTIAL (no double deduction)
    # ==================================================================

    def test_absent_overrides_partial(self):
        """If absent, deduction = daily_rate regardless of late/early values."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),
            check_out=dt(2026, 3, 1, 12, 30),
            x_is_absent=True,
            x_late_minutes=30.0,
            x_early_leave_minutes=60.0,
        )
        self.assertAlmostEqual(att.x_deduction_amount, self.expected_daily_rate, places=2)

    def test_absent_with_zero_late_early(self):
        """Absent with no late/early -> still exactly daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 5, 0),
            x_is_absent=True,
        )
        self.assertAlmostEqual(att.x_deduction_amount, self.expected_daily_rate, places=2)

    # ==================================================================
    # NO VERSION / NO WAGE -> ZERO DEDUCTION
    # ==================================================================

    def test_no_version_no_deduction(self):
        """Employee with wage=0 and no allowances -> all deduction fields = 0."""
        emp_no_contract = self.env['hr.employee'].create({
            'name': 'No Contract Employee',
            'resource_calendar_id': self.calendar.id,
        })
        emp_no_contract.current_version_id.write({
            'wage': 0.0, 'da': 0.0,
            'travel_allowance': 0.0, 'meal_allowance': 0.0,
            'medical_allowance': 0.0, 'other_allowance': 0.0,
        })

        att = self.env['hr.attendance'].create({
            'employee_id': emp_no_contract.id,
            'check_in': dt(2026, 3, 1, 5, 0),
            'check_out': dt(2026, 3, 1, 13, 30),
            'x_late_minutes': 30.0,
        })
        self.assertEqual(att.x_deduction_amount, 0.0)
        self.assertEqual(att.x_daily_rate, 0.0)
        self.assertEqual(att.x_deductible_base, 0.0)

    def test_zero_wage_zero_deduction(self):
        """Wage = 0 with no allowances -> deduction = 0 even if late."""
        zero_emp = self.env['hr.employee'].create({
            'name': 'Zero Wage Employee',
            'resource_calendar_id': self.calendar.id,
        })
        zero_emp.current_version_id.write({
            'name': 'Zero Version',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': self.calendar.id,
            'wage': 0.0,
        })
        zero_emp._compute_current_version_id()

        att = self.env['hr.attendance'].create({
            'employee_id': zero_emp.id,
            'check_in': dt(2026, 3, 1, 5, 30),
            'check_out': dt(2026, 3, 1, 13, 30),
            'x_late_minutes': 30.0,
        })
        self.assertEqual(att.x_deduction_amount, 0.0)

    def test_zero_wage_absent_zero_deduction(self):
        """Absent with zero wage -> deduction = 0."""
        zero_emp = self.env['hr.employee'].create({
            'name': 'Zero Wage Absent',
            'resource_calendar_id': self.calendar.id,
        })
        zero_emp.current_version_id.write({
            'wage': 0.0, 'da': 0.0,
            'travel_allowance': 0.0, 'meal_allowance': 0.0,
            'medical_allowance': 0.0, 'other_allowance': 0.0,
        })
        att = self.env['hr.attendance'].create({
            'employee_id': zero_emp.id,
            'check_in': dt(2026, 3, 1, 5, 0),
            'check_out': dt(2026, 3, 1, 5, 0),
            'x_is_absent': True,
        })
        self.assertEqual(att.x_deduction_amount, 0.0)

    # ==================================================================
    # SCHEDULED MINUTES ALWAYS 480
    # ==================================================================

    def test_scheduled_minutes_always_480(self):
        """Scheduled minutes is always 480 regardless of calendar."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
        )
        self.assertAlmostEqual(att.x_scheduled_minutes, 480.0, places=1)

    def test_scheduled_minutes_480_on_weekend(self):
        """Even on a Friday (weekend), scheduled minutes = 480."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 6, 5, 0),
            check_out=dt(2026, 3, 6, 13, 0),
        )
        self.assertAlmostEqual(att.x_scheduled_minutes, 480.0, places=1)

    def test_scheduled_minutes_same_across_all_days(self):
        """Monday and Friday have the same scheduled minutes (480)."""
        att_sun = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
        )
        att_fri = self._create_attendance(
            check_in=dt(2026, 3, 6, 5, 0),
            check_out=dt(2026, 3, 6, 13, 30),
        )
        self.assertEqual(att_sun.x_scheduled_minutes, att_fri.x_scheduled_minutes)
        self.assertEqual(att_sun.x_scheduled_minutes, 480.0)

    def test_deduction_on_weekend_day(self):
        """Late on a Friday still gets deducted (all days = 480 min)."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 6, 5, 0),   # Friday
            check_out=dt(2026, 3, 6, 13, 30),
            x_late_minutes=60.0,
        )
        expected = (60.0 / 480.0) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    def test_different_schedule_same_deduction(self):
        """Employee with different calendar still uses 480 min for deduction."""
        short_group = self.env['resource.calendar.group'].create({
            'name': 'Short Day Group',
        })
        for day in ['0', '1', '2', '3', '6']:
            self.env['resource.calendar.group.line'].create({
                'name': f'Short Day {day}',
                'calendar_group_id': short_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 9.0,
                'hour_to': 15.0,
            })

        short_calendar = self.env['resource.calendar'].create({
            'name': 'Short Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, short_group.id)],
        })
        short_emp = self.env['hr.employee'].create({
            'name': 'Short Day Employee',
            'resource_calendar_id': short_calendar.id,
        })
        short_emp.current_version_id.write({
            'name': 'Short Version',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': short_calendar.id,
            'wage': 3000.0,
        })
        short_emp._compute_current_version_id()

        att = self.env['hr.attendance'].create({
            'employee_id': short_emp.id,
            'check_in': dt(2026, 3, 1, 6, 0),
            'check_out': dt(2026, 3, 1, 12, 0),
            'x_late_minutes': 30.0,
        })
        # Always 480 regardless of calendar
        self.assertAlmostEqual(att.x_scheduled_minutes, 480.0, places=1)
        expected = (30.0 / 480.0) * (3000.0 / 30.0)
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    # ==================================================================
    # WAGE / ALLOWANCE CHANGE TRIGGERS RECOMPUTATION
    # ==================================================================

    def test_wage_change_recomputes(self):
        """Changing the contract wage should recompute deduction fields."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 2, 5, 0),
            check_out=dt(2026, 3, 2, 13, 30),
            x_late_minutes=30.0,
        )
        old_deduction = att.x_deduction_amount
        self.assertGreater(old_deduction, 0.0)

        self.version.wage = 12000.0
        att.invalidate_recordset()
        new_base = 12000.0 + 500.0 + 300.0 + 200.0
        new_daily = new_base / 30.0
        expected = (30.0 / 480.0) * new_daily
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    def test_allowance_change_recomputes(self):
        """Changing an allowance recomputes deduction."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 3, 5, 0),
            check_out=dt(2026, 3, 3, 13, 30),
            x_late_minutes=30.0,
        )
        old_deduction = att.x_deduction_amount
        self.assertGreater(old_deduction, 0.0)

        self.version.travel_allowance = 1500.0
        att.invalidate_recordset()
        new_base = 6000.0 + 1500.0 + 300.0 + 200.0
        new_daily = new_base / 30.0
        expected = (30.0 / 480.0) * new_daily
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

        # Restore
        self.version.travel_allowance = 500.0

    # ==================================================================
    # PROPORTIONAL DEDUCTION ACCURACY
    # ==================================================================

    def test_proportional_deduction_quarter_day(self):
        """Late 120 min = 25% of 480 -> deduction = 25% of daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=120.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate / 4.0, places=2)

    def test_proportional_deduction_three_quarter_day(self):
        """Late 360 min = 75% of 480 -> deduction = 75% of daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=360.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate * 0.75, places=2)

    # ==================================================================
    # MULTIPLE RECORDS INDEPENDENT
    # ==================================================================

    def test_multiple_records_independent(self):
        """Each attendance record has independent deduction computation."""
        att1 = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=30.0,
        )
        att2 = self._create_attendance(
            check_in=dt(2026, 3, 2, 5, 0),
            check_out=dt(2026, 3, 2, 12, 30),
            x_early_leave_minutes=60.0,
        )
        expected1 = (30.0 / 480.0) * self.expected_daily_rate
        expected2 = (60.0 / 480.0) * self.expected_daily_rate
        self.assertAlmostEqual(att1.x_deduction_amount, expected1, places=2)
        self.assertAlmostEqual(att2.x_deduction_amount, expected2, places=2)
        self.assertNotAlmostEqual(
            att1.x_deduction_amount, att2.x_deduction_amount, places=2)

    # ==================================================================
    # ONLY-ALLOWANCE EMPLOYEE (no base wage)
    # ==================================================================

    def test_only_allowances_no_wage(self):
        """Employee with wage=0 but has allowances -> deduction based on allowances."""
        allowance_emp = self.env['hr.employee'].create({
            'name': 'Allowance Only Employee',
            'resource_calendar_id': self.calendar.id,
        })
        allowance_emp.current_version_id.write({
            'wage': 0.0,
            'travel_allowance': 1000.0,
            'meal_allowance': 500.0,
        })
        allowance_emp._compute_current_version_id()

        att = self.env['hr.attendance'].create({
            'employee_id': allowance_emp.id,
            'check_in': dt(2026, 3, 1, 5, 30),
            'check_out': dt(2026, 3, 1, 13, 30),
            'x_late_minutes': 30.0,
        })
        base = 1500.0
        daily = base / 30.0
        expected = (30.0 / 480.0) * daily
        self.assertAlmostEqual(att.x_deductible_base, 1500.0, places=2)
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)

    # ==================================================================
    # DEDUCTION NEVER NEGATIVE
    # ==================================================================

    def test_deduction_never_negative(self):
        """Even with zero minutes, deduction should be 0, never negative."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=0.0,
            x_early_leave_minutes=0.0,
        )
        self.assertEqual(att.x_deduction_amount, 0.0)
        self.assertGreaterEqual(att.x_deduction_amount, 0.0)

