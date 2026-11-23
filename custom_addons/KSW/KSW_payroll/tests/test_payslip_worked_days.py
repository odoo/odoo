# -*- coding: utf-8 -*-
"""Comprehensive tests for the KSW Payroll payslip worked-day lines,
the ATTDED salary rule, the vacation-return guard, and batch mode.

Employee setup (same as existing tests):
    wage=6000  da=0  travel=500  meal=300  medical=200  other=0  hra=1500
    Deductible base = 6000 + 500 + 300 + 200 = 7000  (HRA excluded)
    Daily rate = round(7000 / 30) = 233
    Scheduled = 8 h/day
"""
from datetime import datetime as dt, date, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPayslipWorkedDays(TransactionCase):
    """Test get_worked_day_lines, compute_sheet guard, and ATTDED rule."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule: Sun-Thu 08:00-16:30 with 1 h break ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Payslip WD Group',
        })
        for day in ['0', '1', '2', '3', '6']:
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
                'hour_to': 13.0,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Payslip WD Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Biometric employee ──
        cls.emp_bio = cls.env['hr.employee'].create({
            'name': 'Bio Employee',
            'resource_calendar_id': cls.calendar.id,
        })
        cls.ver_bio = cls.emp_bio.current_version_id
        cls.ver_bio.write({
            'name': 'Bio Version 2026',
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
            'struct_id': cls.env.ref('om_hr_payroll.structure_base').id,
        })
        cls.emp_bio._compute_current_version_id()

        # ── Attendance-sheet employee ──
        cls.emp_sheet = cls.env['hr.employee'].create({
            'name': 'Sheet Employee',
            'resource_calendar_id': cls.calendar.id,
            'x_is_attendance_sheet': True,
        })
        cls.ver_sheet = cls.emp_sheet.current_version_id
        cls.ver_sheet.write({
            'name': 'Sheet Version 2026',
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
            'struct_id': cls.env.ref('om_hr_payroll.structure_base').id,
        })
        cls.emp_sheet._compute_current_version_id()

        # ── Annual leave type for vacation guard tests ──
        cls.annual_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave',
            'requires_allocation': True,
            'leave_validation_type': 'no_validation',
            'is_annual_leave': True,
        })

        # ── Regular leave type (not annual) ──
        cls.regular_leave_type = cls.env['hr.leave.type'].create({
            'name': 'Sick Leave',
            'requires_allocation': True,
            'leave_validation_type': 'no_validation',
        })

        # ── Expected values ──
        cls.deductible_base = 7000.0
        cls.daily_rate = round(7000.0 / 30.0)  # 233

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _att(self, employee, check_in, check_out=None, **kw):
        """Create an hr.attendance record."""
        vals = {
            'employee_id': employee.id,
            'check_in': check_in,
            'check_out': check_out or check_in,
        }
        vals.update(kw)
        return self.env['hr.attendance'].create(vals)

    def _payslip(self, employee, date_from, date_to):
        """Create a draft payslip."""
        version = employee.current_version_id
        return self.env['hr.payslip'].create({
            'employee_id': employee.id,
            'date_from': date_from,
            'date_to': date_to,
            'version_id': version.id,
            'struct_id': version.struct_id.id,
        })

    def _wd_by_code(self, payslip):
        """Return a dict code → worked_days record for easy lookup."""
        return {wd.code: wd for wd in payslip.worked_days_line_ids}

    def _line_by_code(self, payslip):
        """Return a dict code → payslip.line record for easy lookup."""
        return {ln.code: ln for ln in payslip.line_ids}

    def _create_annual_leave(self, employee, date_from, date_to,
                             return_state='on_vacation'):
        """Create an approved annual leave via SQL to bypass all ORM
        constraints (attendance_ids required, allocation checks, etc.)."""
        date_from_utc = dt.combine(date_from, dt.min.time()) + timedelta(hours=5)
        date_to_utc = dt.combine(date_to, dt.min.time()) + timedelta(hours=13, minutes=30)
        self.env.cr.execute("""
            INSERT INTO hr_leave
                (employee_id, holiday_status_id, state,
                 request_date_from, request_date_to,
                 date_from, date_to,
                 number_of_days, number_of_hours,
                 x_return_state,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'validate',
                 %s, %s, %s, %s,
                 %s, %s,
                 %s,
                 %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            employee.id, self.annual_leave_type.id,
            date_from, date_to, date_from_utc, date_to_utc,
            (date_to - date_from).days + 1,
            ((date_to - date_from).days + 1) * 8.0,
            return_state,
            self.env.uid, self.env.uid,
        ))
        leave_id = self.env.cr.fetchone()[0]
        self.env.invalidate_all()
        return self.env['hr.leave'].browse(leave_id)

    # ==================================================================
    # BIOMETRIC EMPLOYEE — WORKED-DAY LINES
    # ==================================================================

    def test_biometric_all_worked(self):
        """All clean attendance → only WORK100 line, no issue lines."""
        for day in range(1, 6):  # 5 days
            self._att(self.emp_bio,
                      check_in=dt(2026, 3, day, 5, 0),
                      check_out=dt(2026, 3, day, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        wd_vals = self.env['hr.payslip'].get_worked_day_lines(
            self.ver_bio, date(2026, 3, 1), date(2026, 3, 31))

        codes = [w['code'] for w in wd_vals]
        self.assertIn('WORK100', codes)
        self.assertNotIn('ATT_ABS', codes)
        self.assertNotIn('ATT_LATE', codes)
        self.assertNotIn('ATT_EARLY', codes)
        self.assertNotIn('ATT_DED', codes)

        work = next(w for w in wd_vals if w['code'] == 'WORK100')
        self.assertEqual(work['number_of_days'], 5)

    def test_biometric_mixed_issues(self):
        """Mix of clean, absent, late, early → all worked-day codes."""
        # Day 1: clean
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 1, 5, 0),
                  check_out=dt(2026, 3, 1, 13, 30))
        # Day 2: clean
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 2, 5, 0),
                  check_out=dt(2026, 3, 2, 13, 30))
        # Day 3: absent
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 3, 5, 0),
                  check_out=dt(2026, 3, 3, 5, 0),
                  x_is_absent=True)
        # Day 4: 30 min late
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 4, 5, 30),
                  check_out=dt(2026, 3, 4, 13, 30),
                  x_late_minutes=30.0)
        # Day 5: 60 min early
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 5, 5, 0),
                  check_out=dt(2026, 3, 5, 12, 30),
                  x_early_leave_minutes=60.0)

        wd_vals = self.env['hr.payslip'].get_worked_day_lines(
            self.ver_bio, date(2026, 3, 1), date(2026, 3, 31))
        codes = {w['code'] for w in wd_vals}

        self.assertEqual(codes, {'WORK100', 'ATT_ABS', 'ATT_LATE',
                                 'ATT_EARLY', 'ATT_DED'})

        by_code = {w['code']: w for w in wd_vals}
        # WORK100: 4 non-absent (days 1, 2, 4, 5)
        self.assertEqual(by_code['WORK100']['number_of_days'], 4)
        # ATT_ABS: 1 absent
        self.assertEqual(by_code['ATT_ABS']['number_of_days'], 1)
        # ATT_LATE: 1 record
        self.assertEqual(by_code['ATT_LATE']['number_of_days'], 1)
        # ATT_EARLY: 1 record
        self.assertEqual(by_code['ATT_EARLY']['number_of_days'], 1)

    def test_biometric_deduction_sum(self):
        """Deduction amounts from attendance records are summed and rounded."""
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 1, 5, 0),
                  check_out=dt(2026, 3, 1, 5, 0),
                  x_is_absent=True)
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 2, 5, 30),
                  check_out=dt(2026, 3, 2, 13, 30),
                  x_late_minutes=60.0)
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 3, 5, 0),
                  check_out=dt(2026, 3, 3, 12, 30),
                  x_early_leave_minutes=30.0)

        # Read the computed deduction amounts
        atts = self.env['hr.attendance'].search([
            ('employee_id', '=', self.emp_bio.id),
        ], order='check_in asc')
        individual_sum = sum(a.x_deduction_amount for a in atts)

        wd_vals = self.env['hr.payslip'].get_worked_day_lines(
            self.ver_bio, date(2026, 3, 1), date(2026, 3, 31))
        att_ded = next((w for w in wd_vals if w['code'] == 'ATT_DED'), None)

        self.assertIsNotNone(att_ded, 'ATT_DED line should exist')
        self.assertEqual(att_ded['amount'], round(individual_sum))

    # ==================================================================
    # ATTENDANCE-SHEET EMPLOYEE
    # ==================================================================

    def test_sheet_attended_absent(self):
        """Sheet employee: only WORK100 and ATT_ABS (no late/early)."""
        d_from = date(2026, 3, 1)
        d_to = date(2026, 3, 31)

        # Create sheet manually with some absent days
        sheet = self.env['ksw.attendance.sheet'].sudo().create({
            'employee_id': self.emp_sheet.id,
            'month': '3',
            'year': 2026,
        })
        # Mark 5 lines as absent
        absent_dates = [date(2026, 3, d) for d in [5, 10, 15, 20, 25]]
        for line in sheet.line_ids:
            if line.date in absent_dates:
                line.is_attended = False

        # Count actually attended (have hr.attendance records)
        attended = self.env['hr.attendance'].search_count([
            ('employee_id', '=', self.emp_sheet.id),
            ('check_in', '>=', dt.combine(d_from, dt.min.time())),
            ('check_in', '<=', dt.combine(d_to, dt.max.time())),
        ])

        wd_vals = self.env['hr.payslip'].get_worked_day_lines(
            self.ver_sheet, d_from, d_to)
        codes = {w['code'] for w in wd_vals}

        # Should only have WORK100, ATT_ABS, ATT_DED — no ATT_LATE/ATT_EARLY
        self.assertNotIn('ATT_LATE', codes)
        self.assertNotIn('ATT_EARLY', codes)
        self.assertIn('WORK100', codes)
        self.assertIn('ATT_ABS', codes)

        by_code = {w['code']: w for w in wd_vals}
        self.assertEqual(by_code['WORK100']['number_of_days'], attended)
        self.assertEqual(by_code['ATT_ABS']['number_of_days'], 5)

    def test_sheet_absent_deduction(self):
        """Sheet employee absent-day deduction = round(daily_rate × absent)."""
        d_from = date(2026, 3, 1)
        d_to = date(2026, 3, 31)

        sheet = self.env['ksw.attendance.sheet'].sudo().create({
            'employee_id': self.emp_sheet.id,
            'month': '3',
            'year': 2026,
        })
        # Mark 3 lines as absent
        absent_dates = [date(2026, 3, d) for d in [3, 4, 5]]
        for line in sheet.line_ids:
            if line.date in absent_dates:
                line.is_attended = False

        wd_vals = self.env['hr.payslip'].get_worked_day_lines(
            self.ver_sheet, d_from, d_to)
        att_ded = next((w for w in wd_vals if w['code'] == 'ATT_DED'), None)

        self.assertIsNotNone(att_ded)
        expected = round((self.deductible_base / 30.0) * 3)
        self.assertEqual(att_ded['amount'], expected)

    # ==================================================================
    # VACATION RETURN GUARD
    # ==================================================================

    def test_vacation_guard_blocks_unresolved(self):
        """compute_sheet raises when annual leave return is not HR-confirmed."""
        self._create_annual_leave(
            self.emp_bio,
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 10),
            return_state='on_vacation',
        )
        # Create a clean attendance so compute_sheet has something to work with
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 15, 5, 0),
                  check_out=dt(2026, 3, 15, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        with self.assertRaises(ValidationError):
            ps.compute_sheet()

    def test_vacation_guard_blocks_manager_confirmed(self):
        """Still blocked when return is only manager-confirmed (not HR)."""
        self._create_annual_leave(
            self.emp_bio,
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 5),
            return_state='manager_confirmed',
        )
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 15, 5, 0),
                  check_out=dt(2026, 3, 15, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        with self.assertRaises(ValidationError):
            ps.compute_sheet()

    def test_vacation_guard_allows_hr_confirmed(self):
        """compute_sheet succeeds when return is HR-confirmed."""
        self._create_annual_leave(
            self.emp_bio,
            date_from=date(2026, 3, 1),
            date_to=date(2026, 3, 5),
            return_state='hr_confirmed',
        )
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 15, 5, 0),
                  check_out=dt(2026, 3, 15, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        # Should NOT raise
        ps.compute_sheet()
        self.assertTrue(ps.line_ids, 'Payslip lines should be computed')

    def test_vacation_guard_allows_no_annual_leave(self):
        """No annual leave at all → compute_sheet works normally."""
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 1, 5, 0),
                  check_out=dt(2026, 3, 1, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        ps.compute_sheet()
        self.assertTrue(ps.line_ids)

    def test_vacation_guard_ignores_non_annual_leave(self):
        """Regular (non-annual) leave with state=validate → no block."""
        d_from = date(2026, 3, 1)
        d_to = date(2026, 3, 5)
        date_from_utc = dt.combine(d_from, dt.min.time()) + timedelta(hours=5)
        date_to_utc = dt.combine(d_to, dt.min.time()) + timedelta(hours=13, minutes=30)
        self.env.cr.execute("""
            INSERT INTO hr_leave
                (employee_id, holiday_status_id, state,
                 request_date_from, request_date_to,
                 date_from, date_to,
                 number_of_days, number_of_hours,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'validate',
                 %s, %s, %s, %s,
                 5, 40,
                 %s, %s, NOW(), NOW())
        """, (
            self.emp_bio.id, self.regular_leave_type.id,
            d_from, d_to, date_from_utc, date_to_utc,
            self.env.uid, self.env.uid,
        ))
        self.env.invalidate_all()

        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 15, 5, 0),
                  check_out=dt(2026, 3, 15, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        ps.compute_sheet()
        self.assertTrue(ps.line_ids)

    # ==================================================================
    # BATCH MODE — AUTO-POPULATE WORKED DAYS
    # ==================================================================

    def test_batch_auto_populates_worked_days(self):
        """Payslip created without onchange → compute_sheet fills worked_days."""
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 1, 5, 0),
                  check_out=dt(2026, 3, 1, 13, 30))
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 2, 5, 0),
                  check_out=dt(2026, 3, 2, 5, 0),
                  x_is_absent=True)

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        self.assertFalse(ps.worked_days_line_ids,
                         'No worked days yet (no onchange)')

        ps.compute_sheet()

        self.assertTrue(ps.worked_days_line_ids,
                        'compute_sheet should auto-populate worked_days')
        wd = self._wd_by_code(ps)
        self.assertIn('WORK100', wd)
        self.assertIn('ATT_ABS', wd)

    # ==================================================================
    # FULL PAYSLIP COMPUTATION — ATTDED SALARY RULE
    # ==================================================================

    def test_attded_rule_deducts_from_net(self):
        """Full compute: ATTDED subtracts deduction from net salary."""
        # 2 absent days
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 1, 5, 0),
                  check_out=dt(2026, 3, 1, 5, 0),
                  x_is_absent=True)
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 2, 5, 0),
                  check_out=dt(2026, 3, 2, 5, 0),
                  x_is_absent=True)
        # 1 clean day (so WORK100 exists)
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 3, 5, 0),
                  check_out=dt(2026, 3, 3, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        ps.compute_sheet()

        lines = self._line_by_code(ps)
        self.assertIn('ATTDED', lines, 'ATTDED rule should fire')
        self.assertLess(lines['ATTDED'].total, 0,
                        'ATTDED total must be negative (deduction)')

        # Verify the deduction amount matches the ATT_DED worked-day amount
        wd = self._wd_by_code(ps)
        expected_ded = wd['ATT_DED'].amount
        self.assertEqual(lines['ATTDED'].total, -expected_ded)

        # NET should be GROSS - deduction
        self.assertIn('NET', lines)
        self.assertIn('GROSS', lines)
        self.assertEqual(
            lines['NET'].total,
            lines['GROSS'].total + lines['ATTDED'].total,
        )

    def test_no_deduction_no_attded_line(self):
        """Clean attendance → ATTDED rule should NOT fire (condition false)."""
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 1, 5, 0),
                  check_out=dt(2026, 3, 1, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        ps.compute_sheet()

        lines = self._line_by_code(ps)
        # ATTDED should not appear (condition_python = result = bool(worked_days.ATT_DED))
        self.assertNotIn('ATTDED', lines,
                         'ATTDED should not fire when no deductions exist')

    # ==================================================================
    # WHOLE NUMBER ROUNDING
    # ==================================================================

    def test_all_values_whole_numbers(self):
        """Every worked-day value and payslip line total is an integer."""
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 1, 5, 0),
                  check_out=dt(2026, 3, 1, 5, 0),
                  x_is_absent=True)
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 2, 5, 30),
                  check_out=dt(2026, 3, 2, 13, 30),
                  x_late_minutes=30.0)
        self._att(self.emp_bio,
                  check_in=dt(2026, 3, 3, 5, 0),
                  check_out=dt(2026, 3, 3, 13, 30))

        ps = self._payslip(self.emp_bio, date(2026, 3, 1), date(2026, 3, 31))
        ps.compute_sheet()

        for wd in ps.worked_days_line_ids:
            self.assertEqual(wd.number_of_days, round(wd.number_of_days),
                             f'{wd.code} number_of_days should be integer')
            self.assertEqual(wd.number_of_hours, round(wd.number_of_hours),
                             f'{wd.code} number_of_hours should be integer')
            self.assertEqual(wd.amount, round(wd.amount),
                             f'{wd.code} amount should be integer')

        for line in ps.line_ids:
            self.assertEqual(line.total, round(line.total),
                             f'{line.code} total should be integer')

    # ==================================================================
    # SHEET EMPLOYEE — FULL PAYSLIP
    # ==================================================================

    def test_sheet_employee_full_payslip(self):
        """Full payslip for sheet employee with absent days → ATTDED fires."""
        d_from = date(2026, 3, 1)
        d_to = date(2026, 3, 31)

        sheet = self.env['ksw.attendance.sheet'].sudo().create({
            'employee_id': self.emp_sheet.id,
            'month': '3',
            'year': 2026,
        })
        # Mark 2 absent days
        absent_dates = [date(2026, 3, 10), date(2026, 3, 20)]
        for line in sheet.line_ids:
            if line.date in absent_dates:
                line.is_attended = False

        ps = self._payslip(self.emp_sheet, d_from, d_to)
        ps.compute_sheet()

        lines = self._line_by_code(ps)
        wd = self._wd_by_code(ps)

        self.assertIn('ATTDED', lines, 'ATTDED should fire for sheet employee')
        self.assertEqual(wd['ATT_ABS'].number_of_days, 2)
        expected_ded = round((self.deductible_base / 30.0) * 2)
        self.assertEqual(wd['ATT_DED'].amount, expected_ded)
        self.assertEqual(lines['ATTDED'].total, -expected_ded)
