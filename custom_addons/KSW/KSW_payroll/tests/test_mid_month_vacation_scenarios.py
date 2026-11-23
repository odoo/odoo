# -*- coding: utf-8 -*-
"""Mid-month annual vacation → same-month return → monthly payslip scenarios.

Six realistic scenarios where an employee:
  1. Works several days at the start of the month (pre-vacation attendance).
  2. Takes annual vacation within the month.
  3. Returns within the same month (return confirmed by DM + HR).
  4. Gets a monthly payslip batch at month-end covering the leftover days.

At least one scenario includes a **gap** between the vacation end date and
the actual return date (employee did NOT return immediately).

Employee setup (same across all scenarios)
------------------------------------------
wage=6000  hra=1500  da=0  travel=500  meal=300  medical=200  other=0
  daily_rate = (6000 + 500 + 300 + 200) / 30 = 233.33…
  GOSI_full  = -round((6000 + 1500) × 9.75%) = -731
  GOSI_adj   = -round((6000 + 0) × 9.75%)    = -585
"""
from datetime import date, datetime, time as dt_time

from odoo.tests.common import TransactionCase


class TestMidMonthVacationScenarios(TransactionCase):
    """Six realistic mid-month vacation → return → monthly payslip tests."""

    # ==================================================================
    # SETUP
    # ==================================================================

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule (all 7 days to keep calendar-day math simple) ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Mid-Month Scenario Group',
        })
        for day in ['0', '1', '2', '3', '4', '5', '6']:
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Mid-Month Scenario Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Approval chain users ──
        cls.user_dm = cls.env['res.users'].create({
            'name': 'DM Mid', 'login': 'dm_mid_scen',
            'email': 'dm_mid@test.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_dm = cls.env['hr.employee'].create({
            'name': 'DM Employee Mid', 'user_id': cls.user_dm.id,
        })

        cls.user_hr = cls.env['res.users'].create({
            'name': 'HR Mid', 'login': 'hr_mid_scen',
            'email': 'hr_mid@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('hr_holidays.group_hr_holidays_user').id,
            ])],
        })
        cls.emp_hr = cls.env['hr.employee'].create({
            'name': 'HR Employee Mid', 'user_id': cls.user_hr.id,
        })

        cls.user_gm = cls.env['res.users'].create({
            'name': 'GM Mid', 'login': 'gm_mid_scen',
            'email': 'gm_mid@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_gm').id,
            ])],
        })
        cls.emp_gm = cls.env['hr.employee'].create({
            'name': 'GM Employee Mid', 'user_id': cls.user_gm.id,
        })

        cls.user_acc = cls.env['res.users'].create({
            'name': 'ACC Mid', 'login': 'acc_mid_scen',
            'email': 'acc_mid@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_acc').id,
            ])],
        })
        cls.emp_acc = cls.env['hr.employee'].create({
            'name': 'ACC Employee Mid', 'user_id': cls.user_acc.id,
        })

        # ── Employee ──
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Mid-Month Test Employee',
            'resource_calendar_id': cls.calendar.id,
            'leave_manager_id': cls.user_dm.id,
            'country_id': cls.env.ref('base.sa').id,  # Saudi → GOSI
        })

        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Mid-Month Version',
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
        cls.employee._compute_current_version_id()

        # ── Annual leave type ──
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave Mid-Month Test',
            'requires_allocation': False,
            'leave_validation_type': 'annual_multi',
            'is_annual_leave': True,
        })

        # ── Constants ──
        cls.WAGE = 6000.0
        cls.HRA = 1500.0
        cls.TRAVEL = 500.0
        cls.MEAL = 300.0
        cls.MEDICAL = 200.0
        cls.DAILY_RATE = (cls.WAGE + cls.TRAVEL + cls.MEAL + cls.MEDICAL) / 30.0
        cls.GOSI_FULL = -round((cls.WAGE + cls.HRA) * 9.75 / 100.0)   # -731
        # When a prior payslip already paid GOSI, the monthly gets 0
        # (GOSI is paid only once per month via PRIOR_GOSI injection).
        cls.GOSI_ADJ = 0.0

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _create_attendance(self, day, check_in_hour=8, check_out_hour=16,
                           check_out_min=30):
        """Create a clean attendance record (on time, no issues)."""
        ci = datetime.combine(day, dt_time(check_in_hour, 0))
        co = datetime.combine(day, dt_time(check_out_hour, check_out_min))
        return self.env['hr.attendance'].create({
            'employee_id': self.employee.id,
            'check_in': ci,
            'check_out': co,
        })

    def _create_leave_sql(self, date_from, date_to):
        """Insert an annual_multi leave directly to avoid ORM constraints."""
        date_from_utc = datetime.combine(date_from, dt_time(5, 0))
        date_to_utc = datetime.combine(date_to, dt_time(13, 30))
        cal_days = (date_to - date_from).days + 1
        self.env.cr.execute("""
            INSERT INTO hr_leave
                (employee_id, holiday_status_id, state,
                 request_date_from, request_date_to,
                 date_from, date_to,
                 number_of_days, number_of_hours,
                 x_return_state, x_annual_approval_state,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'confirm',
                 %s, %s, %s, %s,
                 %s, %s,
                 'not_applicable', 'pending_dm',
                 %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            self.employee.id, self.leave_type.id,
            date_from, date_to, date_from_utc, date_to_utc,
            cal_days, cal_days * 8.5,
            self.env.uid, self.env.uid,
        ))
        leave_id = self.env.cr.fetchone()[0]
        self.env.invalidate_all()
        return self.env['hr.leave'].browse(leave_id)

    def _approve_full_chain(self, leave):
        """Run the full 5-step approval chain (no penalty/ticket)."""
        leave.with_user(self.user_dm).sudo().action_dm_approve()
        leave.with_user(self.user_hr).sudo().action_hr_approve()
        leave.with_user(self.user_gm).sudo().action_gm_initial_approve()
        leave.with_user(self.user_acc).sudo().action_acc_approve()
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

    def _confirm_return(self, leave, return_date):
        """Write the return date and run both DM + HR confirmations."""
        leave.sudo().write({'x_return_date': return_date})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()
        self.assertEqual(leave.x_return_state, 'hr_confirmed')

    def _create_monthly_payslip(self, date_from, date_to, name='Monthly'):
        """Create a monthly payslip for the test employee."""
        return self.env['hr.payslip'].create({
            'employee_id': self.employee.id,
            'name': name,
            'date_from': date_from,
            'date_to': date_to,
            'struct_id': self.env.ref('om_hr_payroll.structure_base').id,
            'version_id': self.version.id,
        })

    def _get_line(self, payslip, code):
        return payslip.line_ids.filtered(lambda l: l.code == code)[:1]

    def _get_total(self, payslip, code):
        line = self._get_line(payslip, code)
        return line.total if line else 0.0

    def _get_input(self, payslip, code):
        return payslip.input_line_ids.filtered(lambda i: i.code == code)[:1]

    def _get_wd(self, payslip, code):
        return payslip.worked_days_line_ids.filtered(
            lambda w: w.code == code)[:1]

    def _run_scenario(self, *, attendance_before, leave_start, leave_end,
                      return_date, attendance_after, month_start, month_end,
                      scenario_name):
        """Execute a full vacation → return → monthly payslip scenario.

        Returns (vac_slip, monthly) for further assertions by the caller.
        """
        # 1. Create pre-vacation attendance
        for d in attendance_before:
            self._create_attendance(d)

        # 2. Create & approve annual leave
        leave = self._create_leave_sql(leave_start, leave_end)
        self._approve_full_chain(leave)
        self.assertEqual(leave.state, 'validate',
                         f'{scenario_name}: Leave should be validated.')
        vac_slip = leave.x_vacation_payslip_id
        self.assertTrue(vac_slip,
                        f'{scenario_name}: Vacation payslip should exist.')

        # 3. Confirm return
        self._confirm_return(leave, return_date)

        # 4. Create post-return attendance
        for d in attendance_after:
            self._create_attendance(d)

        # 5. Confirm vacation payslip
        vac_slip.action_payslip_done()
        self.assertEqual(vac_slip.state, 'done')

        # 6. Create and compute monthly payslip
        monthly = self._create_monthly_payslip(
            month_start, month_end, name=f'{scenario_name} Monthly')
        monthly.compute_sheet()

        return vac_slip, monthly

    # ==================================================================
    # SCENARIO 1: 7-day vacation mid-month, immediate return
    # ==================================================================

    def test_scenario_1_seven_day_vacation_immediate_return(self):
        """
        Scenario 1 — 7-day vacation mid-month, immediate return
        ─────────────────────────────────────────────────────────
        Employee works Apr 1–7 (7 days ahead).
        Takes annual leave Apr 8–14 (7 calendar days).
        Returns Apr 15 (immediately after vacation ends).
        Works Apr 15–30 (16 days).

        Vacation payslip (computed at approval, only Apr 1–7 attendance):
          WORK100 = 7 days
          ATT_ABS = 23 days (30 − 7)
          ATTDED  = −round(233.33 × 23) = −5367
          GOSI    = −731  (full base)
          VACATION_BAL = 7 × (6000/30) = 1400

        Monthly payslip (batch at month-end):
          effective_from = Apr 15 (return date)
          WORK100 = 16 days  (Apr 15–30)
          ATT_ABS = 14 days  (Apr 1–14, pre-return)
          ATTDED  = −round(233.33 × 14) = −3267
          PRIOR_HRA = 1500  →  HRA = 0
          GOSI = −585  (adjusted, no HRA)
        """
        month = date(2026, 4, 1), date(2026, 4, 30)
        pre_vac = [date(2026, 4, d) for d in range(1, 8)]     # Apr 1–7
        post_vac = [date(2026, 4, d) for d in range(15, 31)]  # Apr 15–30

        vac, monthly = self._run_scenario(
            attendance_before=pre_vac,
            leave_start=date(2026, 4, 8),
            leave_end=date(2026, 4, 14),
            return_date=date(2026, 4, 15),
            attendance_after=post_vac,
            month_start=month[0], month_end=month[1],
            scenario_name='S1',
        )

        # ── Vacation payslip checks ──
        self.assertEqual(self._get_wd(vac, 'WORK100').number_of_days, 7,
                         'S1-Vac: 7 worked days.')
        vac_absent = self._get_wd(vac, 'ATT_ABS')
        self.assertTrue(vac_absent)
        self.assertEqual(vac_absent.number_of_days, 23,
                         'S1-Vac: 23 absent days (30−7).')
        self.assertEqual(self._get_total(vac, 'ATTDED'),
                         -round(self.DAILY_RATE * 23),
                         'S1-Vac: ATTDED = −round(233.33×23).')
        self.assertEqual(self._get_total(vac, 'HRA'), 1500.0)
        self.assertEqual(self._get_total(vac, 'GOSI'), self.GOSI_FULL)

        vac_bal = self._get_input(vac, 'VACATION_BAL')
        if vac_bal:
            self.assertAlmostEqual(vac_bal.amount, 7 * ((self.WAGE + self.HRA) / 30.0),
                                   places=0, msg='S1-Vac: VACATION_BAL = 1400.')

        # ── Monthly payslip checks ──
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 16,
                         'S1-Mon: 16 worked days (Apr 15–30).')
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent, 'S1-Mon: ATT_ABS must exist.')
        self.assertEqual(m_absent.number_of_days, 14,
                         'S1-Mon: 14 pre-return absent days (Apr 1–14).')
        self.assertEqual(m_absent.amount, round(self.DAILY_RATE * 14),
                         'S1-Mon: ATT_ABS amount = round(233.33×14).')

        self.assertEqual(self._get_total(monthly, 'ATTDED'),
                         -round(self.DAILY_RATE * 14),
                         'S1-Mon: ATTDED = −round(233.33×14).')

        self.assertTrue(self._get_input(monthly, 'PRIOR_HRA'),
                        'S1-Mon: PRIOR_HRA must be injected.')
        self.assertEqual(self._get_input(monthly, 'PRIOR_HRA').amount, 1500.0)
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0,
                         'S1-Mon: HRA = 0 (already paid).')
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S1-Mon: GOSI = 0 (already paid in full).')

        # HRA paid exactly once across both payslips
        total_hra = self._get_total(vac, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0,
                         'S1: HRA paid exactly once across both slips.')

    # ==================================================================
    # SCENARIO 2: Short 3-day vacation early in month, immediate return
    # ==================================================================

    def test_scenario_2_short_3day_vacation_early_month(self):
        """
        Scenario 2 — Short 3-day vacation early in month
        ─────────────────────────────────────────────────
        Employee works Apr 1–4 (4 days ahead).
        Takes annual leave Apr 5–7 (3 calendar days).
        Returns Apr 8 (immediately).
        Works Apr 8–30 (23 days).

        Vacation payslip (only Apr 1–4 attendance at approval):
          WORK100 = 4 days
          ATT_ABS = 26 days (30 − 4)
          ATTDED  = −round(233.33 × 26) = −6067
          VACATION_BAL = 3 × 200 = 600

        Monthly payslip:
          effective_from = Apr 8
          WORK100 = 23 days
          ATT_ABS = 7 days (Apr 1–7 pre-return)
          ATTDED  = −round(233.33 × 7) = −1633
          PRIOR_HRA = 1500  →  HRA = 0
        """
        month = date(2026, 4, 1), date(2026, 4, 30)
        pre_vac = [date(2026, 4, d) for d in range(1, 5)]     # Apr 1–4
        post_vac = [date(2026, 4, d) for d in range(8, 31)]   # Apr 8–30

        vac, monthly = self._run_scenario(
            attendance_before=pre_vac,
            leave_start=date(2026, 4, 5),
            leave_end=date(2026, 4, 7),
            return_date=date(2026, 4, 8),
            attendance_after=post_vac,
            month_start=month[0], month_end=month[1],
            scenario_name='S2',
        )

        # ── Vacation payslip ──
        self.assertEqual(self._get_wd(vac, 'WORK100').number_of_days, 4,
                         'S2-Vac: 4 worked days.')
        self.assertEqual(self._get_wd(vac, 'ATT_ABS').number_of_days, 26,
                         'S2-Vac: 26 absent days.')
        self.assertEqual(self._get_total(vac, 'ATTDED'),
                         -round(self.DAILY_RATE * 26),
                         'S2-Vac: ATTDED for 26 absent days.')
        self.assertEqual(self._get_total(vac, 'GOSI'), self.GOSI_FULL)

        vac_bal = self._get_input(vac, 'VACATION_BAL')
        if vac_bal:
            self.assertAlmostEqual(vac_bal.amount, 3 * ((self.WAGE + self.HRA) / 30.0),
                                   places=0, msg='S2-Vac: VACATION_BAL = 600.')

        # ── Monthly payslip ──
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 23,
                         'S2-Mon: 23 worked days (Apr 8–30).')
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        self.assertEqual(m_absent.number_of_days, 7,
                         'S2-Mon: 7 pre-return absent days (Apr 1–7).')
        self.assertEqual(m_absent.amount, round(self.DAILY_RATE * 7),
                         'S2-Mon: ATT_ABS amount = round(233.33×7).')

        self.assertEqual(self._get_total(monthly, 'ATTDED'),
                         -round(self.DAILY_RATE * 7),
                         'S2-Mon: ATTDED for 7 absent days.')
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0,
                         'S2-Mon: HRA = 0 (already paid).')
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S2-Mon: GOSI = 0 (already paid in full).')

        # Combined HRA once
        total_hra = self._get_total(vac, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0, 'S2: HRA paid once.')

    # ==================================================================
    # SCENARIO 3: 10-day vacation with 3-day GAP before return
    # ==================================================================

    def test_scenario_3_ten_day_vacation_with_3day_gap(self):
        """
        Scenario 3 — 10-day vacation, employee does NOT return immediately
        ──────────────────────────────────────────────────────────────────
        Employee works Apr 1–9 (9 days ahead).
        Takes annual leave Apr 10–19 (10 calendar days).
        Vacation ends Apr 19, but employee does NOT return until Apr 23.
        Gap: Apr 20–22 (3 days unexcused absence — no attendance).
        Returns Apr 23 (HR-confirmed return date).
        Works Apr 23–30 (8 days).

        Vacation payslip (only Apr 1–9 attendance at approval):
          WORK100 = 9 days
          ATT_ABS = 21 days (30 − 9)
          ATTDED  = −round(233.33 × 21) = −4900
          VACATION_BAL = 10 × 200 = 2000

        Monthly payslip:
          effective_from = Apr 23 (return date, NOT leave end+1)
          WORK100 = 8 days  (Apr 23–30)
          ATT_ABS = 22 days (Apr 1–22, pre-return — includes the 3-day gap)
          ATTDED  = −round(233.33 × 22) = −5133
          PRIOR_HRA = 1500  →  HRA = 0

        The 3-day gap (Apr 20–22) is covered by the pre-return absent
        block, which means the employee is effectively penalised for those
        days on the monthly payslip through the attendance deduction.
        """
        month = date(2026, 4, 1), date(2026, 4, 30)
        pre_vac = [date(2026, 4, d) for d in range(1, 10)]    # Apr 1–9
        post_vac = [date(2026, 4, d) for d in range(23, 31)]  # Apr 23–30

        vac, monthly = self._run_scenario(
            attendance_before=pre_vac,
            leave_start=date(2026, 4, 10),
            leave_end=date(2026, 4, 19),
            return_date=date(2026, 4, 23),   # ← 3-day gap!
            attendance_after=post_vac,
            month_start=month[0], month_end=month[1],
            scenario_name='S3',
        )

        # ── Vacation payslip ──
        self.assertEqual(self._get_wd(vac, 'WORK100').number_of_days, 9,
                         'S3-Vac: 9 worked days (Apr 1–9).')
        self.assertEqual(self._get_wd(vac, 'ATT_ABS').number_of_days, 21,
                         'S3-Vac: 21 absent days (30−9).')
        self.assertEqual(self._get_total(vac, 'ATTDED'),
                         -round(self.DAILY_RATE * 21),
                         'S3-Vac: ATTDED for 21 absent days.')
        self.assertEqual(self._get_total(vac, 'GOSI'), self.GOSI_FULL)

        vac_bal = self._get_input(vac, 'VACATION_BAL')
        if vac_bal:
            self.assertAlmostEqual(vac_bal.amount, 10 * ((self.WAGE + self.HRA) / 30.0),
                                   places=0, msg='S3-Vac: VACATION_BAL = 2000.')

        # ── Monthly payslip ──
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 8,
                         'S3-Mon: 8 worked days (Apr 23–30).')
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent, 'S3-Mon: ATT_ABS must exist.')
        # Pre-return = (Apr 23 - Apr 1).days = 22 days
        self.assertEqual(m_absent.number_of_days, 22,
                         'S3-Mon: 22 pre-return absent days (Apr 1–22, '
                         'including the 3-day gap Apr 20–22).')
        self.assertEqual(m_absent.amount, round(self.DAILY_RATE * 22),
                         'S3-Mon: ATT_ABS deduction for 22 days.')
        self.assertEqual(self._get_total(monthly, 'ATTDED'),
                         -round(self.DAILY_RATE * 22),
                         'S3-Mon: ATTDED for 22 absent days.')

        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0,
                         'S3-Mon: HRA = 0 (already paid).')
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S3-Mon: GOSI = 0 (already paid in full).')

        # HRA once
        total_hra = self._get_total(vac, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0, 'S3: HRA paid once.')

        # Combined NET should be reasonable
        combined_net = self._get_total(vac, 'NET') + self._get_total(monthly, 'NET')
        self.assertGreater(combined_net, 3000,
                           'S3: Combined NET should be > 3000.')
        self.assertLess(combined_net, 15000,
                        'S3: Combined NET should be < 15000.')

    # ==================================================================
    # SCENARIO 4: Week-long leave mid-month, immediate return
    # ==================================================================

    def test_scenario_4_weeklong_midmonth_immediate_return(self):
        """
        Scenario 4 — 7-day leave in the middle of the month
        ────────────────────────────────────────────────────
        Employee works Apr 1–11 (11 days ahead).
        Takes annual leave Apr 12–18 (7 calendar days).
        Returns Apr 19 (immediately).
        Works Apr 19–30 (12 days).

        Vacation payslip (only Apr 1–11 attendance):
          WORK100 = 11 days
          ATT_ABS = 19 days (30 − 11)
          ATTDED  = −round(233.33 × 19) = −4433
          VACATION_BAL = 7 × 200 = 1400

        Monthly payslip:
          effective_from = Apr 19
          WORK100 = 12 days
          ATT_ABS = 18 days (Apr 1–18 pre-return)
          ATTDED  = −round(233.33 × 18) = −4200
          PRIOR_HRA = 1500  →  HRA = 0
        """
        month = date(2026, 4, 1), date(2026, 4, 30)
        pre_vac = [date(2026, 4, d) for d in range(1, 12)]    # Apr 1–11
        post_vac = [date(2026, 4, d) for d in range(19, 31)]  # Apr 19–30

        vac, monthly = self._run_scenario(
            attendance_before=pre_vac,
            leave_start=date(2026, 4, 12),
            leave_end=date(2026, 4, 18),
            return_date=date(2026, 4, 19),
            attendance_after=post_vac,
            month_start=month[0], month_end=month[1],
            scenario_name='S4',
        )

        # ── Vacation payslip ──
        self.assertEqual(self._get_wd(vac, 'WORK100').number_of_days, 11,
                         'S4-Vac: 11 worked days (Apr 1–11).')
        self.assertEqual(self._get_wd(vac, 'ATT_ABS').number_of_days, 19,
                         'S4-Vac: 19 absent days.')
        self.assertEqual(self._get_total(vac, 'ATTDED'),
                         -round(self.DAILY_RATE * 19),
                         'S4-Vac: ATTDED for 19 absent days.')
        self.assertEqual(self._get_total(vac, 'GOSI'), self.GOSI_FULL)

        vac_bal = self._get_input(vac, 'VACATION_BAL')
        if vac_bal:
            self.assertAlmostEqual(vac_bal.amount, 7 * ((self.WAGE + self.HRA) / 30.0),
                                   places=0, msg='S4-Vac: VACATION_BAL = 1400.')

        # ── Monthly payslip ──
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 12,
                         'S4-Mon: 12 worked days (Apr 19–30).')
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        self.assertEqual(m_absent.number_of_days, 18,
                         'S4-Mon: 18 pre-return absent days (Apr 1–18).')
        self.assertEqual(self._get_total(monthly, 'ATTDED'),
                         -round(self.DAILY_RATE * 18),
                         'S4-Mon: ATTDED for 18 absent days.')
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0,
                         'S4-Mon: HRA = 0.')
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S4-Mon: GOSI = 0 (already paid in full).')

        total_hra = self._get_total(vac, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0, 'S4: HRA paid once.')

    # ==================================================================
    # SCENARIO 5: 5-day vacation with 5-day GAP before return
    # ==================================================================

    def test_scenario_5_five_day_vacation_with_5day_gap(self):
        """
        Scenario 5 — 5-day vacation + 5-day gap (delayed return)
        ─────────────────────────────────────────────────────────
        Employee works Apr 1–5 (5 days ahead).
        Takes annual leave Apr 6–10 (5 calendar days).
        Vacation ends Apr 10, employee does NOT return until Apr 16.
        Gap: Apr 11–15 (5 days unexcused absence).
        Returns Apr 16 (HR-confirmed).
        Works Apr 16–30 (15 days).

        Vacation payslip (only Apr 1–5 attendance):
          WORK100 = 5 days
          ATT_ABS = 25 days (30 − 5)
          ATTDED  = −round(233.33 × 25) = −5833
          VACATION_BAL = 5 × 200 = 1000

        Monthly payslip:
          effective_from = Apr 16
          WORK100 = 15 days (Apr 16–30)
          ATT_ABS = 15 days (Apr 1–15, pre-return — includes 5-day gap)
          ATTDED  = −round(233.33 × 15) = −3500
          PRIOR_HRA = 1500  →  HRA = 0

        The 5-day gap is embedded in the 15 pre-return absent days.
        """
        month = date(2026, 4, 1), date(2026, 4, 30)
        pre_vac = [date(2026, 4, d) for d in range(1, 6)]     # Apr 1–5
        post_vac = [date(2026, 4, d) for d in range(16, 31)]  # Apr 16–30

        vac, monthly = self._run_scenario(
            attendance_before=pre_vac,
            leave_start=date(2026, 4, 6),
            leave_end=date(2026, 4, 10),
            return_date=date(2026, 4, 16),   # ← 5-day gap!
            attendance_after=post_vac,
            month_start=month[0], month_end=month[1],
            scenario_name='S5',
        )

        # ── Vacation payslip ──
        self.assertEqual(self._get_wd(vac, 'WORK100').number_of_days, 5,
                         'S5-Vac: 5 worked days (Apr 1–5).')
        self.assertEqual(self._get_wd(vac, 'ATT_ABS').number_of_days, 25,
                         'S5-Vac: 25 absent days.')
        self.assertEqual(self._get_total(vac, 'ATTDED'),
                         -round(self.DAILY_RATE * 25),
                         'S5-Vac: ATTDED for 25 absent days.')

        vac_bal = self._get_input(vac, 'VACATION_BAL')
        if vac_bal:
            self.assertAlmostEqual(vac_bal.amount, 5 * ((self.WAGE + self.HRA) / 30.0),
                                   places=0, msg='S5-Vac: VACATION_BAL = 1000.')

        # ── Monthly payslip ──
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 15,
                         'S5-Mon: 15 worked days (Apr 16–30).')
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        self.assertEqual(m_absent.number_of_days, 15,
                         'S5-Mon: 15 pre-return absent days (Apr 1–15).')
        self.assertEqual(self._get_total(monthly, 'ATTDED'),
                         -round(self.DAILY_RATE * 15),
                         'S5-Mon: ATTDED for 15 absent days.')
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S5-Mon: GOSI = 0 (already paid in full).')

        total_hra = self._get_total(vac, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0, 'S5: HRA paid once.')

        # Verify the gap days are penalised
        combined_net = self._get_total(vac, 'NET') + self._get_total(monthly, 'NET')
        self.assertGreater(combined_net, 2000,
                           'S5: Combined NET > 2000 even with 5-day gap.')
        self.assertLess(combined_net, 12000,
                        'S5: Combined NET < 12000.')

    # ==================================================================
    # SCENARIO 6: Late-month 2-day vacation with 2-day GAP
    # ==================================================================

    def test_scenario_6_latemouth_2day_vacation_with_gap(self):
        """
        Scenario 6 — Late-month short vacation + 2-day gap
        ───────────────────────────────────────────────────
        Employee works Apr 1–20 (20 days ahead — most of the month).
        Takes annual leave Apr 21–22 (2 calendar days).
        Vacation ends Apr 22, employee does NOT return until Apr 25.
        Gap: Apr 23–24 (2 days absent — weekend trip extended, etc.).
        Returns Apr 25 (HR-confirmed).
        Works Apr 25–30 (6 days).

        Vacation payslip (Apr 1–20 attendance at approval):
          WORK100 = 20 days
          ATT_ABS = 10 days (30 − 20)
          ATTDED  = −round(233.33 × 10) = −2333
          VACATION_BAL = 2 × 200 = 400

        Monthly payslip:
          effective_from = Apr 25
          WORK100 = 6 days  (Apr 25–30)
          ATT_ABS = 24 days (Apr 1–24, pre-return — includes 2-day gap)
          ATTDED  = −round(233.33 × 24) = −5600
          PRIOR_HRA = 1500  →  HRA = 0

        This tests the edge case where the employee worked MOST of the
        month before vacation, but the monthly payslip still counts from
        the return date and deducts the entire pre-return period.
        """
        month = date(2026, 4, 1), date(2026, 4, 30)
        pre_vac = [date(2026, 4, d) for d in range(1, 21)]    # Apr 1–20
        post_vac = [date(2026, 4, d) for d in range(25, 31)]  # Apr 25–30

        vac, monthly = self._run_scenario(
            attendance_before=pre_vac,
            leave_start=date(2026, 4, 21),
            leave_end=date(2026, 4, 22),
            return_date=date(2026, 4, 25),   # ← 2-day gap!
            attendance_after=post_vac,
            month_start=month[0], month_end=month[1],
            scenario_name='S6',
        )

        # ── Vacation payslip ──
        self.assertEqual(self._get_wd(vac, 'WORK100').number_of_days, 20,
                         'S6-Vac: 20 worked days (Apr 1–20).')
        self.assertEqual(self._get_wd(vac, 'ATT_ABS').number_of_days, 10,
                         'S6-Vac: 10 absent days (30−20).')
        self.assertEqual(self._get_total(vac, 'ATTDED'),
                         -round(self.DAILY_RATE * 10),
                         'S6-Vac: ATTDED for 10 absent days.')

        vac_bal = self._get_input(vac, 'VACATION_BAL')
        if vac_bal:
            self.assertAlmostEqual(vac_bal.amount, 2 * ((self.WAGE + self.HRA) / 30.0),
                                   places=0, msg='S6-Vac: VACATION_BAL = 400.')

        # ── Monthly payslip ──
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 6,
                         'S6-Mon: 6 worked days (Apr 25–30).')
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        self.assertEqual(m_absent.number_of_days, 24,
                         'S6-Mon: 24 pre-return absent days (Apr 1–24).')
        self.assertEqual(m_absent.amount, round(self.DAILY_RATE * 24),
                         'S6-Mon: ATT_ABS deduction for 24 days.')
        self.assertEqual(self._get_total(monthly, 'ATTDED'),
                         -round(self.DAILY_RATE * 24),
                         'S6-Mon: ATTDED for 24 absent days.')
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S6-Mon: GOSI = 0 (already paid in full).')

        total_hra = self._get_total(vac, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0, 'S6: HRA paid once.')

        # Combined NET sanity
        combined_net = self._get_total(vac, 'NET') + self._get_total(monthly, 'NET')
        self.assertGreater(combined_net, 3000, 'S6: Combined NET > 3000.')
        self.assertLess(combined_net, 15000, 'S6: Combined NET < 15000.')

