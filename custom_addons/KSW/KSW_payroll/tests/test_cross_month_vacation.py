# -*- coding: utf-8 -*-
"""Cross-month annual vacation payslip tests.

Validates that when an employee's annual vacation spans multiple calendar
months, a vacation payslip is created for **each** affected month so the
employee receives HRA and GOSI for every month.

Scenarios
---------
S1: 2-month vacation (Mar 25 – Apr 10), immediate return Apr 11.
    Two vacation payslips (March + April).  April monthly payslip
    uses PRIOR_HRA/PRIOR_GOSI from the April vacation payslip.

S2: 2-month with gap (Mar 20 – Apr 15), return Apr 20 (5-day gap).
    Two vacation payslips.  April monthly payslip counts from Apr 20
    with 19 pre-return absent days (including 5-day gap penalty).

S3: Single-month regression (Apr 5 – Apr 12), return Apr 13.
    Only ONE vacation payslip for April.  Existing behaviour preserved.

S4: 3-month vacation (Jan 28 – Mar 5), return Mar 6.
    Three vacation payslips (Jan, Feb, Mar).  March monthly payslip
    has PRIOR_HRA/PRIOR_GOSI from March vacation payslip.

Employee setup (same for all)
-----------------------------
wage=6000  hra=1500  da=0  travel=500  meal=300  medical=200  other=0
  daily_rate = (6000 + 500 + 300 + 200) / 30 = 233.33…
  GOSI_full  = -round((6000 + 1500) × 9.75%) = -731
"""
from datetime import date, datetime, time as dt_time

from odoo.tests.common import TransactionCase


class TestCrossMonthVacation(TransactionCase):
    """Tests for cross-month annual vacation payslip generation."""

    # ==================================================================
    # SETUP
    # ==================================================================

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule (7 days/week to keep math simple) ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Cross-Month Test Group',
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
            'name': 'Cross-Month Test Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Approval chain users ──
        cls.user_dm = cls.env['res.users'].create({
            'name': 'DM Cross', 'login': 'dm_cross_scen',
            'email': 'dm_cross@test.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_dm = cls.env['hr.employee'].create({
            'name': 'DM Employee Cross', 'user_id': cls.user_dm.id,
        })

        cls.user_hr = cls.env['res.users'].create({
            'name': 'HR Cross', 'login': 'hr_cross_scen',
            'email': 'hr_cross@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('hr_holidays.group_hr_holidays_user').id,
            ])],
        })
        cls.emp_hr = cls.env['hr.employee'].create({
            'name': 'HR Employee Cross', 'user_id': cls.user_hr.id,
        })

        cls.user_gm = cls.env['res.users'].create({
            'name': 'GM Cross', 'login': 'gm_cross_scen',
            'email': 'gm_cross@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_gm').id,
            ])],
        })
        cls.emp_gm = cls.env['hr.employee'].create({
            'name': 'GM Employee Cross', 'user_id': cls.user_gm.id,
        })

        cls.user_acc = cls.env['res.users'].create({
            'name': 'ACC Cross', 'login': 'acc_cross_scen',
            'email': 'acc_cross@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_acc').id,
            ])],
        })
        cls.emp_acc = cls.env['hr.employee'].create({
            'name': 'ACC Employee Cross', 'user_id': cls.user_acc.id,
        })

        # ── Employee ──
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Cross-Month Test Employee',
            'resource_calendar_id': cls.calendar.id,
            'leave_manager_id': cls.user_dm.id,
            'country_id': cls.env.ref('base.sa').id,
        })

        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Cross-Month Version',
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
            'name': 'Annual Leave Cross-Month Test',
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

    # ==================================================================
    # HELPERS
    # ==================================================================

    def _create_attendance(self, day, check_in_hour=8, check_out_hour=16,
                           check_out_min=30):
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
        """Run the full 5-step approval chain."""
        leave.with_user(self.user_dm).sudo().action_dm_approve()
        leave.with_user(self.user_hr).sudo().action_hr_approve()
        leave.with_user(self.user_gm).sudo().action_gm_initial_approve()
        leave.with_user(self.user_acc).sudo().action_acc_approve()
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

    def _confirm_return(self, leave, return_date):
        leave.sudo().write({'x_return_date': return_date})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()
        self.assertEqual(leave.x_return_state, 'hr_confirmed')

    def _create_monthly_payslip(self, date_from, date_to, name='Monthly'):
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

    # ==================================================================
    # S1: 2-month vacation (Mar 25 – Apr 10), immediate return Apr 11
    # ==================================================================

    def test_s1_two_month_vacation_immediate_return(self):
        """
        S1 — Vacation spans March and April, immediate return
        ─────────────────────────────────────────────────────
        Pre-vacation attendance: Mar 1–24 (24 days).
        Annual leave: Mar 25 – Apr 10 (17 calendar days).
        Return: Apr 11 (immediately).
        Post-return attendance: Apr 11–30 (20 days).

        Expected:
        - TWO vacation payslips created (March + April).
        - March vac payslip: HRA=1500, GOSI=-731, has VACATION_BAL.
        - April vac payslip: HRA=1500, GOSI=-731, NO VACATION_BAL.
        - April monthly payslip: PRIOR_HRA=1500 (from Apr vac),
          HRA=0, GOSI=0.  effective_from=Apr 11.
        """
        # Pre-vacation attendance (March)
        for d in range(1, 25):
            self._create_attendance(date(2026, 3, d))

        # Create & approve leave (Mar 25 – Apr 10)
        leave = self._create_leave_sql(date(2026, 3, 25), date(2026, 4, 10))
        self._approve_full_chain(leave)
        self.assertEqual(leave.state, 'validate', 'S1: Leave validated.')

        # Verify TWO vacation payslips created
        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 2,
                         'S1: Two vacation payslips should be created.')

        # Identify March and April payslips
        mar_vac = vac_payslips.filtered(
            lambda p: p.date_from.month == 3)
        apr_vac = vac_payslips.filtered(
            lambda p: p.date_from.month == 4)
        self.assertTrue(mar_vac, 'S1: March vacation payslip exists.')
        self.assertTrue(apr_vac, 'S1: April vacation payslip exists.')

        # Primary payslip should be the March one
        self.assertEqual(leave.x_vacation_payslip_id.id, mar_vac.id,
                         'S1: Primary payslip is the first (March).')

        # March vac payslip checks
        self.assertEqual(self._get_total(mar_vac, 'HRA'), 1500.0,
                         'S1-MarVac: HRA = 1500.')
        self.assertEqual(self._get_total(mar_vac, 'GOSI'), self.GOSI_FULL,
                         'S1-MarVac: GOSI = -731.')
        vac_bal = self._get_input(mar_vac, 'VACATION_BAL')
        self.assertTrue(vac_bal, 'S1-MarVac: VACATION_BAL input exists.')

        # April vac payslip checks
        self.assertEqual(self._get_total(apr_vac, 'HRA'), 1500.0,
                         'S1-AprVac: HRA = 1500.')
        self.assertEqual(self._get_total(apr_vac, 'GOSI'), self.GOSI_FULL,
                         'S1-AprVac: GOSI = -731.')
        apr_vac_bal = self._get_input(apr_vac, 'VACATION_BAL')
        self.assertFalse(apr_vac_bal,
                         'S1-AprVac: NO VACATION_BAL on second payslip.')

        # Confirm return and create post-return attendance
        self._confirm_return(leave, date(2026, 4, 11))
        for d in range(11, 31):
            self._create_attendance(date(2026, 4, d))

        # Confirm both vacation payslips
        mar_vac.action_payslip_done()
        apr_vac.action_payslip_done()

        # Create April monthly payslip
        monthly = self._create_monthly_payslip(
            date(2026, 4, 1), date(2026, 4, 30), name='S1 Apr Monthly')
        monthly.compute_sheet()

        # April monthly should have PRIOR_HRA from April vac payslip
        prior_hra = self._get_input(monthly, 'PRIOR_HRA')
        self.assertTrue(prior_hra, 'S1-AprMon: PRIOR_HRA injected.')
        self.assertEqual(prior_hra.amount, 1500.0)
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0,
                         'S1-AprMon: HRA = 0 (already paid).')
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S1-AprMon: GOSI = 0 (already paid).')

        # Monthly WORK100 should be 20 days (Apr 11–30)
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 20,
                         'S1-AprMon: 20 worked days (Apr 11–30).')

        # Monthly ATT_ABS = 10 pre-return absent days (Apr 1–10)
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent, 'S1-AprMon: ATT_ABS exists.')
        self.assertEqual(m_absent.number_of_days, 10,
                         'S1-AprMon: 10 pre-return absent days (Apr 1–10).')

        # HRA paid exactly once per month
        mar_hra = self._get_total(mar_vac, 'HRA')
        apr_hra = self._get_total(apr_vac, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(mar_hra, 1500.0, 'S1: March HRA = 1500.')
        self.assertEqual(apr_hra, 1500.0, 'S1: April HRA = 1500 (once).')

    # ==================================================================
    # S2: 2-month with gap (Mar 20 – Apr 15), return Apr 20
    # ==================================================================

    def test_s2_two_month_vacation_with_gap(self):
        """
        S2 — Cross-month vacation with 5-day gap before return
        ──────────────────────────────────────────────────────
        Pre-vacation attendance: Mar 1–19 (19 days).
        Annual leave: Mar 20 – Apr 15 (27 calendar days).
        Vacation ends Apr 15, employee returns Apr 20 (5-day gap).
        Post-return attendance: Apr 20–30 (11 days).

        Expected:
        - TWO vacation payslips (March + April).
        - April monthly payslip: effective_from=Apr 20 (NOT Apr 16).
          Pre-return absent = 19 days (Apr 1–19, includes 5-day gap).
        """
        # Pre-vacation attendance (March)
        for d in range(1, 20):
            self._create_attendance(date(2026, 3, d))

        # Create & approve leave (Mar 20 – Apr 15)
        leave = self._create_leave_sql(date(2026, 3, 20), date(2026, 4, 15))
        self._approve_full_chain(leave)
        self.assertEqual(leave.state, 'validate', 'S2: Leave validated.')

        # Verify TWO vacation payslips
        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 2,
                         'S2: Two vacation payslips created.')

        mar_vac = vac_payslips.filtered(lambda p: p.date_from.month == 3)
        apr_vac = vac_payslips.filtered(lambda p: p.date_from.month == 4)

        # Both have HRA and GOSI
        self.assertEqual(self._get_total(mar_vac, 'HRA'), 1500.0)
        self.assertEqual(self._get_total(mar_vac, 'GOSI'), self.GOSI_FULL)
        self.assertEqual(self._get_total(apr_vac, 'HRA'), 1500.0)
        self.assertEqual(self._get_total(apr_vac, 'GOSI'), self.GOSI_FULL)

        # VACATION_BAL only on March (first)
        self.assertTrue(self._get_input(mar_vac, 'VACATION_BAL'))
        self.assertFalse(self._get_input(apr_vac, 'VACATION_BAL'))

        # Confirm return with 5-day gap
        self._confirm_return(leave, date(2026, 4, 20))
        for d in range(20, 31):
            self._create_attendance(date(2026, 4, d))

        # Confirm vacation payslips
        mar_vac.action_payslip_done()
        apr_vac.action_payslip_done()

        # Create April monthly payslip
        monthly = self._create_monthly_payslip(
            date(2026, 4, 1), date(2026, 4, 30), name='S2 Apr Monthly')
        monthly.compute_sheet()

        # Monthly should count from return date (Apr 20)
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 11,
                         'S2-AprMon: 11 worked days (Apr 20–30).')

        # Pre-return absent = 19 days (Apr 1–19, includes the 5-day gap)
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        self.assertEqual(m_absent.number_of_days, 19,
                         'S2-AprMon: 19 pre-return absent days.')

        # PRIOR_HRA from April vacation payslip
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0)

        # HRA once per month
        self.assertEqual(
            self._get_total(apr_vac, 'HRA') + self._get_total(monthly, 'HRA'),
            1500.0, 'S2: April HRA paid exactly once.')

    # ==================================================================
    # S3: Single-month regression (Apr 5 – Apr 12), return Apr 13
    # ==================================================================

    def test_s3_single_month_regression(self):
        """
        S3 — Single-month vacation (regression test)
        ─────────────────────────────────────────────
        Verify that a vacation within a single month still produces
        exactly ONE vacation payslip (no regression from cross-month
        changes).

        Pre-vacation attendance: Apr 1–4 (4 days).
        Annual leave: Apr 5 – Apr 12 (8 calendar days).
        Return: Apr 13.
        Post-return attendance: Apr 13–30 (18 days).
        """
        for d in range(1, 5):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 5), date(2026, 4, 12))
        self._approve_full_chain(leave)
        self.assertEqual(leave.state, 'validate', 'S3: Leave validated.')

        # Only ONE vacation payslip
        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 1,
                         'S3: Exactly one vacation payslip (single month).')

        # Primary link matches the only payslip
        self.assertEqual(leave.x_vacation_payslip_id.id,
                         vac_payslips[0].id)

        # Has VACATION_BAL
        self.assertTrue(self._get_input(vac_payslips[0], 'VACATION_BAL'))

        # HRA and GOSI present
        self.assertEqual(self._get_total(vac_payslips[0], 'HRA'), 1500.0)
        self.assertEqual(self._get_total(vac_payslips[0], 'GOSI'),
                         self.GOSI_FULL)

        # Confirm return and create post-return attendance
        self._confirm_return(leave, date(2026, 4, 13))
        for d in range(13, 31):
            self._create_attendance(date(2026, 4, d))

        vac_payslips[0].action_payslip_done()

        # Monthly payslip
        monthly = self._create_monthly_payslip(
            date(2026, 4, 1), date(2026, 4, 30), name='S3 Apr Monthly')
        monthly.compute_sheet()

        # PRIOR_HRA injected
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0)

        # 18 worked days (Apr 13–30), 12 pre-return absent (Apr 1–12)
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 18)
        self.assertEqual(self._get_wd(monthly, 'ATT_ABS').number_of_days, 12)

    # ==================================================================
    # S4: 3-month vacation (Jan 28 – Mar 5), return Mar 6
    # ==================================================================

    def test_s4_three_month_vacation(self):
        """
        S4 — Vacation spans 3 calendar months
        ──────────────────────────────────────
        Pre-vacation attendance: May 1–27 (27 days).
        Annual leave: May 28 – Jul 5 (39 calendar days).
        Return: Jul 6.
        Post-return attendance: Jul 6–31 (26 days).

        Expected:
        - THREE vacation payslips (May, Jun, Jul).
        - VACATION_BAL only on the first (May).
        - Each payslip has its own HRA=1500 and GOSI=-731.
        - July monthly payslip gets PRIOR_HRA/PRIOR_GOSI from
          the July vacation payslip only (not May or Jun).
        """
        # Remove any mandatory days / public holidays that might conflict
        self.env['resource.calendar.leaves'].sudo().search([
            ('resource_id', '=', False),
        ]).unlink()

        # Pre-vacation attendance (May)
        for d in range(1, 28):
            self._create_attendance(date(2026, 5, d))

        # Create & approve leave (May 28 – Jul 5)
        leave = self._create_leave_sql(date(2026, 5, 28), date(2026, 7, 5))
        self._approve_full_chain(leave)
        self.assertEqual(leave.state, 'validate', 'S4: Leave validated.')

        # Verify THREE vacation payslips
        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 3,
                         'S4: Three vacation payslips (May, Jun, Jul).')

        may_vac = vac_payslips.filtered(lambda p: p.date_from.month == 5)
        jun_vac = vac_payslips.filtered(lambda p: p.date_from.month == 6)
        jul_vac = vac_payslips.filtered(lambda p: p.date_from.month == 7)

        self.assertTrue(may_vac and jun_vac and jul_vac,
                        'S4: Payslips exist for all 3 months.')

        # VACATION_BAL only on May (first)
        self.assertTrue(self._get_input(may_vac, 'VACATION_BAL'),
                        'S4: VACATION_BAL on May payslip.')
        self.assertFalse(self._get_input(jun_vac, 'VACATION_BAL'),
                         'S4: No VACATION_BAL on June payslip.')
        self.assertFalse(self._get_input(jul_vac, 'VACATION_BAL'),
                         'S4: No VACATION_BAL on July payslip.')

        # Each month gets its own HRA and GOSI
        for label, vac_slip in [('May', may_vac), ('Jun', jun_vac),
                                ('Jul', jul_vac)]:
            self.assertEqual(self._get_total(vac_slip, 'HRA'), 1500.0,
                             f'S4-{label}Vac: HRA = 1500.')
            self.assertEqual(self._get_total(vac_slip, 'GOSI'),
                             self.GOSI_FULL,
                             f'S4-{label}Vac: GOSI = -731.')

        # Confirm return and post-return attendance
        self._confirm_return(leave, date(2026, 7, 6))
        for d in range(6, 32):
            self._create_attendance(date(2026, 7, d))

        # Confirm all vacation payslips
        for vac_slip in vac_payslips:
            vac_slip.action_payslip_done()

        # Create July monthly payslip
        monthly = self._create_monthly_payslip(
            date(2026, 7, 1), date(2026, 7, 31), name='S4 Jul Monthly')
        monthly.compute_sheet()

        # PRIOR_HRA from July vacation payslip ONLY (not May/Jun)
        prior_hra = self._get_input(monthly, 'PRIOR_HRA')
        self.assertTrue(prior_hra, 'S4-JulMon: PRIOR_HRA injected.')
        self.assertEqual(prior_hra.amount, 1500.0,
                         'S4-JulMon: PRIOR_HRA = 1500 (from Jul vac only).')

        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0,
                         'S4-JulMon: HRA = 0.')
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0,
                         'S4-JulMon: GOSI = 0.')

        # 26 worked days (Jul 6–31), 5 pre-return absent (Jul 1–5)
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 26,
                         'S4-JulMon: 26 worked days (Jul 6–31).')
        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        self.assertEqual(m_absent.number_of_days, 5,
                         'S4-JulMon: 5 pre-return absent days (Jul 1–5).')

        # Total HRA across all payslips = 1500 per month
        total_jul_hra = (self._get_total(jul_vac, 'HRA')
                         + self._get_total(monthly, 'HRA'))
        self.assertEqual(total_jul_hra, 1500.0,
                         'S4: July HRA paid exactly once.')

    # ==================================================================
    # S5: Cross-month — no monthly payslip for vacation-start month
    # ==================================================================

    def test_s5_no_double_hra_for_non_return_month(self):
        """
        S5 — Verify that a monthly payslip for the vacation-start month
        does NOT incorrectly inject PRIOR_HRA from a different month's
        vacation payslip.

        Vacation: Mar 25 – Apr 10.
        March vac payslip exists, April vac payslip exists.
        If someone creates a March monthly payslip, PRIOR_HRA should
        come from the March vac payslip (same month), NOT from the
        April vac payslip.
        """
        for d in range(1, 25):
            self._create_attendance(date(2026, 3, d))

        leave = self._create_leave_sql(date(2026, 3, 25), date(2026, 4, 10))
        self._approve_full_chain(leave)

        vac_payslips = leave.x_vacation_payslip_ids
        mar_vac = vac_payslips.filtered(lambda p: p.date_from.month == 3)
        apr_vac = vac_payslips.filtered(lambda p: p.date_from.month == 4)

        # Confirm return
        self._confirm_return(leave, date(2026, 4, 11))

        # Confirm vacation payslips
        mar_vac.action_payslip_done()
        apr_vac.action_payslip_done()

        # Create March monthly payslip (edge case — not typical)
        mar_monthly = self._create_monthly_payslip(
            date(2026, 3, 1), date(2026, 3, 31), name='S5 Mar Monthly')
        mar_monthly.compute_sheet()

        # PRIOR_HRA should be 1500 (from MARCH vac payslip only)
        prior_hra = self._get_input(mar_monthly, 'PRIOR_HRA')
        self.assertTrue(prior_hra, 'S5: PRIOR_HRA injected on March monthly.')
        self.assertEqual(prior_hra.amount, 1500.0,
                         'S5: PRIOR_HRA = 1500 (from March vac, not April).')
        self.assertEqual(self._get_total(mar_monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(mar_monthly, 'GOSI'), 0.0)

        # April monthly payslip
        for d in range(11, 31):
            self._create_attendance(date(2026, 4, d))

        apr_monthly = self._create_monthly_payslip(
            date(2026, 4, 1), date(2026, 4, 30), name='S5 Apr Monthly')
        apr_monthly.compute_sheet()

        # PRIOR_HRA = 1500 (from APRIL vac payslip, not March)
        apr_prior = self._get_input(apr_monthly, 'PRIOR_HRA')
        self.assertTrue(apr_prior, 'S5: PRIOR_HRA injected on April monthly.')
        self.assertEqual(apr_prior.amount, 1500.0,
                         'S5: PRIOR_HRA = 1500 (from April vac).')
        self.assertEqual(self._get_total(apr_monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(apr_monthly, 'GOSI'), 0.0)


