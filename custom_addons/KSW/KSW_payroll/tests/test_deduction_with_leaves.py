# -*- coding: utf-8 -*-
"""Comprehensive tests for deduction calculations WITH leave coverage.
These tests verify that approved time-off reduces net minutes and therefore
reduces the deduction amount, and that refusing/resetting leaves restores
the original deduction.
Deduction rules (hardcoded):
    All employees: 30 days/month, 8 hours/day = 480 min/day.
    Deduction = (deductible_minutes / 480) * daily_rate, capped at daily_rate.
Contract:
    wage=6000  da=0  travel=500  meal=300  medical=200  other=0  hra=1500
    Deductible base = 6000+500+300+200 = 7000  (HRA excluded)
    Daily rate = 7000 / 30 = 233.333...
"""
from datetime import datetime as dt, date, timedelta
from odoo.tests.common import TransactionCase
class TestDeductionWithLeaves(TransactionCase):
    """Verify deduction recalculation when leaves cover attendance issues."""
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # ── Work schedule: Sun-Thu 08:00-16:30 with 1h break ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Deduction Leave Group',
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
            'name': 'Test Deduction Leave Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Deduction Leave Employee',
            'resource_calendar_id': cls.calendar.id,
        })
        # Update the auto-created version
        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Test Version',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': cls.calendar.id,
            'wage': 6000.0,
            'da': 0.0,
            'travel_allowance': 500.0,
            'meal_allowance': 300.0,
            'medical_allowance': 200.0,
            'other_allowance': 0.0,
            'hra': 1500.0,
        })
        cls.employee._compute_current_version_id()
        # Non-allocation leave type (for attendance-based leaves)
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Test Permission',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'hour',
        })
        # Allocation-based leave type (for absent-day leaves)
        cls.leave_type_day = cls.env['hr.leave.type'].create({
            'name': 'Test Sick Leave',
            'requires_allocation': False,
            'leave_validation_type': 'no_validation',
            'request_unit': 'day',
        })
        cls.expected_base = 7000.0
        cls.expected_daily_rate = 7000.0 / 30.0
        cls.expected_scheduled_minutes = 480.0  # hardcoded 8h
    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _create_attendance(self, check_in, check_out=None, **kwargs):
        """Create an hr.attendance record."""
        vals = {
            'employee_id': self.employee.id,
            'check_in': check_in,
            'check_out': check_out or check_in,
        }
        vals.update(kwargs)
        return self.env['hr.attendance'].create(vals)
    def _create_approved_leave_for_attendance(self, attendance, leave_type=None,
                                              accepted_minutes_override=None):
        """Create an attendance-based hr.leave that covers the given attendance,
        directly in 'validate' state using SQL to bypass _check_validity.
        For tests we focus on the net-minute -> deduction pipeline, not
        leave-approval flow (which is tested elsewhere).
        """
        lt = leave_type or self.leave_type
        att_date = attendance.check_in.date()
        # Build date_from / date_to in UTC  (08:00 / 16:30 Riyadh = 05:00 / 13:30 UTC)
        date_from_utc = dt.combine(att_date, dt.min.time()) + timedelta(hours=5)
        date_to_utc = dt.combine(att_date, dt.min.time()) + timedelta(hours=13, minutes=30)
        # Create leave directly with all required fields set
        leave = self.env['hr.leave'].with_context(
            leave_skip_state_check=True,
            tracking_disable=True,
            leave_fast_create=True,
            mail_create_nosubscribe=True,
        ).create({
            'employee_id': self.employee.id,
            'holiday_status_id': lt.id,
            'request_date_from': att_date,
            'request_date_to': att_date,
            'date_from': date_from_utc,
            'date_to': date_to_utc,
            'x_attendance_ids': [(4, attendance.id)],
        })
        # Generate attendance lines
        leave._generate_attendance_lines()
        # Override accepted_minutes if requested
        if accepted_minutes_override is not None:
            for line in leave.x_attendance_line_ids:
                line.accepted_minutes = accepted_minutes_override
        # Flush all pending ORM writes to DB before raw SQL
        self.env.flush_all()
        # Set state to 'validate' directly via SQL to bypass _check_validity
        self.env.cr.execute(
            "UPDATE hr_leave SET state = 'validate' WHERE id = %s",
            [leave.id],
        )
        # Fully invalidate ALL caches so ORM re-reads from DB
        self.env.invalidate_all()
        # Trigger recomputation of net minutes on the attendance record(s)
        attendance._compute_is_covered()
        attendance._compute_net_minutes()
        return leave
    def _refuse_leave(self, leave):
        """Set leave back to 'refuse' state via SQL (bypassing _check_validity)."""
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_leave SET state = 'refuse' WHERE id = %s",
            [leave.id],
        )
        self.env.invalidate_all()
        # Recompute net minutes on related attendance records
        for att in leave.x_attendance_ids:
            att._compute_is_covered()
            att._compute_net_minutes()
    # ==================================================================
    # LEAVE FULLY COVERS LATE -> DEDUCTION DROPS TO ZERO
    # ==================================================================
    def test_leave_covers_all_late_minutes(self):
        """Approved leave covering all late minutes -> deduction = 0."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),   # 08:30 Riyadh, 30 min late
            check_out=dt(2026, 3, 1, 13, 30),  # 16:30 Riyadh
            x_late_minutes=30.0,
        )
        # Before leave: deduction > 0
        self.assertGreater(att.x_deduction_amount, 0.0)
        self._create_approved_leave_for_attendance(att)
        self.assertEqual(att.x_net_late_minutes, 0.0,
                         "Net late minutes should be 0 after approved leave.")
        self.assertEqual(att.x_deduction_amount, 0.0,
                         "Deduction should be 0 when leave fully covers late minutes.")
    def test_leave_covers_all_early_leave_minutes(self):
        """Approved leave covering all early leave minutes -> deduction = 0."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),    # 08:00 Riyadh
            check_out=dt(2026, 3, 1, 12, 30),  # 15:30 Riyadh, 60 min early
            x_early_leave_minutes=60.0,
        )
        self.assertGreater(att.x_deduction_amount, 0.0)
        self._create_approved_leave_for_attendance(att)
        self.assertEqual(att.x_net_early_leave_minutes, 0.0)
        self.assertEqual(att.x_deduction_amount, 0.0)
    def test_leave_covers_combined_late_and_early(self):
        """Leave covers both late + early leave -> deduction = 0."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 20),   # 08:20 Riyadh, 20 min late
            check_out=dt(2026, 3, 1, 12, 50),  # 15:50 Riyadh, 40 min early
            x_late_minutes=20.0,
            x_early_leave_minutes=40.0,
        )
        self.assertGreater(att.x_deduction_amount, 0.0)
        self._create_approved_leave_for_attendance(att)
        self.assertEqual(att.x_net_late_minutes, 0.0)
        self.assertEqual(att.x_net_early_leave_minutes, 0.0)
        self.assertEqual(att.x_deduction_amount, 0.0)
    # ==================================================================
    # PARTIAL LEAVE COVERAGE -> REDUCED (NOT ZERO) DEDUCTION
    # ==================================================================
    def test_partial_late_coverage_reduces_deduction(self):
        """Leave accepts only 10 of 30 late minutes -> deduction for remaining 20."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 2, 5, 30),   # Monday, 30 min late
            check_out=dt(2026, 3, 2, 13, 30),
            x_late_minutes=30.0,
        )
        original_deduction = att.x_deduction_amount
        self._create_approved_leave_for_attendance(att, accepted_minutes_override=10.0)
        self.assertAlmostEqual(att.x_net_late_minutes, 20.0, places=1,
                               msg="Net late should be 30 - 10 = 20.")
        expected = (20.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
        self.assertLess(att.x_deduction_amount, original_deduction)
    def test_partial_early_coverage_reduces_deduction(self):
        """Leave accepts 30 of 60 early leave minutes -> deduction halved."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 2, 5, 0),
            check_out=dt(2026, 3, 2, 12, 30),
            x_early_leave_minutes=60.0,
        )
        self._create_approved_leave_for_attendance(att, accepted_minutes_override=30.0)
        self.assertAlmostEqual(att.x_net_early_leave_minutes, 30.0, places=1)
        expected = (30.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
    # ==================================================================
    # ABSENT COVERED BY LEAVE -> DEDUCTION = 0
    # ==================================================================
    def test_absent_covered_by_leave_no_deduction(self):
        """Approved leave covering an absent day -> deduction = 0."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 5, 0),
            x_is_absent=True,
        )
        self.assertAlmostEqual(att.x_deduction_amount,
                               self.expected_daily_rate, places=2)
        self._create_approved_leave_for_attendance(
            att, leave_type=self.leave_type_day)
        self.assertFalse(att.x_net_is_absent,
                         "Net absent should be False when covered by leave.")
        self.assertEqual(att.x_deduction_amount, 0.0,
                         "Deduction should be 0 when absence is covered.")
    # ==================================================================
    # LEAVE REFUSED -> DEDUCTION RESTORED
    # ==================================================================
    def test_refuse_leave_restores_deduction(self):
        """Refusing a previously approved leave restores the original deduction."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 3, 5, 30),   # Tuesday
            check_out=dt(2026, 3, 3, 13, 30),
            x_late_minutes=30.0,
        )
        original_deduction = att.x_deduction_amount
        self.assertGreater(original_deduction, 0.0)
        leave = self._create_approved_leave_for_attendance(att)
        self.assertEqual(att.x_deduction_amount, 0.0)
        # Refuse the leave
        self._refuse_leave(leave)
        self.assertAlmostEqual(att.x_deduction_amount, original_deduction, places=2,
                               msg="Refusing the leave should restore the deduction.")
    # ==================================================================
    # UNAPPROVED LEAVE HAS NO EFFECT ON DEDUCTION
    # ==================================================================
    def test_draft_leave_no_effect_on_deduction(self):
        """A draft (unsubmitted) leave should NOT reduce deduction."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=30.0,
        )
        original_deduction = att.x_deduction_amount
        att_date = att.check_in.date()
        date_from_utc = dt.combine(att_date, dt.min.time()) + timedelta(hours=5)
        date_to_utc = dt.combine(att_date, dt.min.time()) + timedelta(hours=13, minutes=30)
        # Create leave in draft state (NOT approved)
        self.env['hr.leave'].with_context(
            leave_skip_state_check=True,
            tracking_disable=True,
            leave_fast_create=True,
            mail_create_nosubscribe=True,
        ).create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': att_date,
            'request_date_to': att_date,
            'date_from': date_from_utc,
            'date_to': date_to_utc,
            'x_attendance_ids': [(4, att.id)],
        })
        att.invalidate_recordset()
        self.assertAlmostEqual(att.x_deduction_amount, original_deduction, places=2,
                               msg="Draft leave should not affect deduction.")
    # ==================================================================
    # DEDUCTION CAP STILL APPLIES WITH LEAVE COVERAGE
    # ==================================================================
    def test_deduction_capped_after_partial_leave(self):
        """Large early leave partially covered: remaining still capped at daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 10),
            check_out=dt(2026, 3, 1, 5, 10),
            x_early_leave_minutes=500.0,  # Exceeds 480
        )
        # Without leave: capped at daily rate
        self.assertAlmostEqual(att.x_deduction_amount,
                               self.expected_daily_rate, places=2)
        # Approve leave covering 100 of 500 minutes
        self._create_approved_leave_for_attendance(att, accepted_minutes_override=100.0)
        # Remaining: 400 min out of 480 scheduled
        remaining = 400.0
        expected = min(
            (remaining / self.expected_scheduled_minutes) * self.expected_daily_rate,
            self.expected_daily_rate,
        )
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
    # ==================================================================
    # LARGE EARLY LEAVE (NEAR FULL DAY) WITH CORRECT DEDUCTION
    # ==================================================================
    def test_large_early_leave_proportional_deduction(self):
        """469 min early leave out of 480 -> proportional deduction < daily rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 10),
            check_out=dt(2026, 3, 1, 5, 10),
            x_early_leave_minutes=469.0,
        )
        # 469/480 < 1 -> proportional, NOT capped
        expected = (469.0 / 480.0) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
        self.assertLess(att.x_deduction_amount, self.expected_daily_rate)
    def test_large_early_leave_under_scheduled(self):
        """440 min early leave out of 480 -> proportional deduction."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 5, 10),
            x_early_leave_minutes=440.0,
        )
        expected = (440.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
        self.assertLess(att.x_deduction_amount, self.expected_daily_rate)
    # ==================================================================
    # DIFFERENT SCHEDULE EMPLOYEE -> STILL 480 MIN
    # ==================================================================
    def test_deduction_with_shorter_schedule(self):
        """Employee with 6h schedule: deduction still uses 480 min (hardcoded)."""
        short_group = self.env['resource.calendar.group'].create({
            'name': 'Short Day Group DL',
        })
        for day in ['0', '1', '2', '3', '6']:
            self.env['resource.calendar.group.line'].create({
                'name': f'Short {day}',
                'calendar_group_id': short_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 9.0,
                'hour_to': 15.0,
            })
        short_cal = self.env['resource.calendar'].create({
            'name': 'Short Calendar DL',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, short_group.id)],
        })
        short_emp = self.env['hr.employee'].create({
            'name': 'Short Day DL Employee',
            'resource_calendar_id': short_cal.id,
        })
        short_emp.current_version_id.write({
            'name': 'Short Version DL',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': short_cal.id,
            'wage': 3000.0,
        })
        short_emp._compute_current_version_id()
        att = self.env['hr.attendance'].create({
            'employee_id': short_emp.id,
            'check_in': dt(2026, 3, 1, 6, 30),  # 09:30 Riyadh, 30 min late
            'check_out': dt(2026, 3, 1, 12, 0),
            'x_late_minutes': 30.0,
        })
        # Hardcoded 480 min regardless of schedule
        self.assertAlmostEqual(att.x_scheduled_minutes, 480.0, places=1)
        expected = (30.0 / 480.0) * (3000.0 / 30.0)
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
    # ==================================================================
    # NO CALENDAR -> STILL 480 MINUTES
    # ==================================================================
    def test_no_calendar_480(self):
        """Employee with no calendar at all -> scheduled = 480 min."""
        no_cal_emp = self.env['hr.employee'].create({
            'name': 'No Calendar Employee',
        })
        no_cal_emp.current_version_id.write({
            'wage': 3000.0,
        })
        no_cal_emp._compute_current_version_id()
        att = self.env['hr.attendance'].create({
            'employee_id': no_cal_emp.id,
            'check_in': dt(2026, 3, 1, 5, 30),
            'check_out': dt(2026, 3, 1, 13, 30),
            'x_late_minutes': 30.0,
        })
        self.assertAlmostEqual(att.x_scheduled_minutes, 480.0, places=1)
        expected = (30.0 / 480.0) * (3000.0 / 30.0)
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
    # ==================================================================
    # DEDUCTION PROPORTIONAL FORMULA VERIFICATION
    # ==================================================================
    def test_deduction_formula_exact(self):
        """Verify: deduction = (net_late + net_early) / 480 * daily_rate."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 45),
            check_out=dt(2026, 3, 1, 12, 45),
            x_late_minutes=45.0,
            x_early_leave_minutes=45.0,
        )
        deductible = 45.0 + 45.0
        expected = (deductible / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
        # 90/480 = 0.1875 -> 18.75% of daily rate
        self.assertAlmostEqual(
            att.x_deduction_amount, self.expected_daily_rate * (90.0 / 480.0), places=2)
    def test_deduction_formula_one_quarter(self):
        """120 min late out of 480 = 1/4 -> deduction = daily_rate / 4."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=120.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount,
            self.expected_daily_rate / 4.0,
            places=2,
        )
    def test_deduction_formula_one_third(self):
        """160 min late out of 480 = 1/3 -> deduction = daily_rate / 3."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=160.0,
        )
        self.assertAlmostEqual(
            att.x_deduction_amount,
            self.expected_daily_rate / 3.0,
            places=2,
        )
    # ==================================================================
    # MULTIPLE ATTENDANCE RECORDS WITH SINGLE LEAVE
    # ==================================================================
    def test_leave_covers_multiple_attendances(self):
        """One leave covering two attendance records -> both deductions to 0."""
        att1 = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=30.0,
        )
        att2 = self._create_attendance(
            check_in=dt(2026, 3, 2, 5, 30),
            check_out=dt(2026, 3, 2, 13, 30),
            x_late_minutes=30.0,
        )
        self.assertGreater(att1.x_deduction_amount, 0.0)
        self.assertGreater(att2.x_deduction_amount, 0.0)
        # Create leave covering both records
        att1_date = att1.check_in.date()
        att2_date = att2.check_in.date()
        min_date = min(att1_date, att2_date)
        max_date = max(att1_date, att2_date)
        date_from_utc = dt.combine(min_date, dt.min.time()) + timedelta(hours=5)
        date_to_utc = dt.combine(max_date, dt.min.time()) + timedelta(hours=13, minutes=30)
        leave = self.env['hr.leave'].with_context(
            leave_skip_state_check=True,
            tracking_disable=True,
            leave_fast_create=True,
            mail_create_nosubscribe=True,
        ).create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'request_date_from': min_date,
            'request_date_to': max_date,
            'date_from': date_from_utc,
            'date_to': date_to_utc,
            'x_attendance_ids': [(4, att1.id), (4, att2.id)],
        })
        leave._generate_attendance_lines()
        # Approve via SQL
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE hr_leave SET state = 'validate' WHERE id = %s",
            [leave.id],
        )
        self.env.invalidate_all()
        for att in (att1, att2):
            att._compute_is_covered()
            att._compute_net_minutes()
        self.assertEqual(att1.x_net_late_minutes, 0.0)
        self.assertEqual(att2.x_net_late_minutes, 0.0)
        self.assertEqual(att1.x_deduction_amount, 0.0)
        self.assertEqual(att2.x_deduction_amount, 0.0)
    # ==================================================================
    # EDGE CASE: ZERO DEDUCTIBLE MINUTES (NO ISSUE)
    # ==================================================================
    def test_zero_deductible_minutes(self):
        """No issues -> deduction = 0 even with valid schedule and wage."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 0),
            check_out=dt(2026, 3, 1, 13, 30),
        )
        self.assertEqual(att.x_deduction_amount, 0.0)
        self.assertAlmostEqual(att.x_scheduled_minutes, 480.0, places=1)
        self.assertAlmostEqual(att.x_deductible_base, 7000.0, places=2)
    # ==================================================================
    # DEDUCTION RECOMPUTES WHEN NET MINUTES CHANGE
    # ==================================================================
    def test_net_minutes_change_recomputes_deduction(self):
        """Changing late minutes should trigger deduction recompute."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=60.0,
        )
        deduction_60 = att.x_deduction_amount
        expected_60 = (60.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(deduction_60, expected_60, places=2)
        # Reduce late minutes
        att.write({'x_late_minutes': 30.0})
        att.invalidate_recordset()
        expected_30 = (30.0 / self.expected_scheduled_minutes) * self.expected_daily_rate
        self.assertAlmostEqual(att.x_deduction_amount, expected_30, places=2)
        self.assertLess(att.x_deduction_amount, deduction_60)
    # ==================================================================
    # DEDUCTION NEVER NEGATIVE (even with weird data)
    # ==================================================================
    def test_deduction_never_negative_with_leave(self):
        """Even if leave covers more than actual minutes, deduction >= 0."""
        att = self._create_attendance(
            check_in=dt(2026, 3, 1, 5, 30),
            check_out=dt(2026, 3, 1, 13, 30),
            x_late_minutes=30.0,
        )
        self._create_approved_leave_for_attendance(att)
        self.assertGreaterEqual(att.x_deduction_amount, 0.0)
        self.assertGreaterEqual(att.x_net_late_minutes, 0.0)
    # ==================================================================
    # DEDUCTION CONSISTENCY: daily_rate IS ALWAYS base / 30
    # ==================================================================
    def test_daily_rate_consistency(self):
        """Verify daily_rate = deductible_base / 30 for all records."""
        for day_offset in range(5):  # Sun-Thu
            att = self._create_attendance(
                check_in=dt(2026, 3, 1 + day_offset, 5, 30),
                check_out=dt(2026, 3, 1 + day_offset, 13, 30),
                x_late_minutes=30.0,
            )
            self.assertAlmostEqual(
                att.x_daily_rate, att.x_deductible_base / 30.0, places=2,
                msg=f"Daily rate should always be base/30 (day offset {day_offset}).")
    # ==================================================================
    # DEDUCTION WITH ONLY da ALLOWANCE
    # ==================================================================
    def test_deduction_with_da_only(self):
        """Employee with wage + da only -> deduction uses wage + da."""
        da_emp = self.env['hr.employee'].create({
            'name': 'DA Only Employee',
            'resource_calendar_id': self.calendar.id,
        })
        da_emp.current_version_id.write({
            'wage': 5000.0,
            'da': 1000.0,
            'travel_allowance': 0.0,
            'meal_allowance': 0.0,
            'medical_allowance': 0.0,
            'other_allowance': 0.0,
        })
        da_emp._compute_current_version_id()
        att = self.env['hr.attendance'].create({
            'employee_id': da_emp.id,
            'check_in': dt(2026, 3, 1, 5, 30),
            'check_out': dt(2026, 3, 1, 13, 30),
            'x_late_minutes': 45.0,
        })
        base = 6000.0
        daily = base / 30.0
        expected = (45.0 / self.expected_scheduled_minutes) * daily
        self.assertAlmostEqual(att.x_deductible_base, base, places=2)
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2)
    # ==================================================================
    # SCENARIO FROM ISSUE: attendance #8102
    # Early leave 469 min with 480 scheduled, base 3250
    # ==================================================================
    def test_scenario_8102_like(self):
        """Reproduce the original bug scenario: early leave 469 min
        with base 3250 and hardcoded 480 min.
        Deduction should be (469/480) * (3250/30) = 105.85."""
        scenario_emp = self.env['hr.employee'].create({
            'name': 'Scenario 8102 Employee',
            'resource_calendar_id': self.calendar.id,
        })
        scenario_emp.current_version_id.write({
            'wage': 2000.0,
            'da': 250.0,
            'other_allowance': 1000.0,
        })
        scenario_emp._compute_current_version_id()
        att = self.env['hr.attendance'].create({
            'employee_id': scenario_emp.id,
            'check_in': dt(2026, 3, 26, 5, 10, 52),  # 08:10 Riyadh
            'check_out': dt(2026, 3, 26, 5, 10, 52),  # same (barely showed up)
            'x_early_leave_minutes': 469.0,
        })
        # Verify base and daily rate
        self.assertAlmostEqual(att.x_deductible_base, 3250.0, places=2)
        self.assertAlmostEqual(att.x_daily_rate, 3250.0 / 30.0, places=2)
        self.assertAlmostEqual(att.x_scheduled_minutes, 480.0, places=1)
        # The key assertion: deduction should be (469/480) * daily_rate
        expected = (469.0 / 480.0) * (3250.0 / 30.0)
        self.assertAlmostEqual(att.x_deduction_amount, expected, places=2,
                               msg="Deduction should be proportional.")
        # It must be less than the daily rate
        self.assertLess(att.x_deduction_amount, att.x_daily_rate,
                        msg="Deduction for 469/480 must be less than daily rate.")
        # Approximate check: ~105.85
        self.assertAlmostEqual(att.x_deduction_amount, 105.85, places=1)
