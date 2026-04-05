# -*- coding: utf-8 -*-
"""End-to-end test: vacation payslip + monthly payslip overlap scenario.

Scenario
--------
Employee works April 1–10  (10 days attendance, no issues).
Takes annual vacation April 11–15  (5 calendar days).
Returns April 16 → confirmed by DM + HR.
Works April 16–30  (15 days attendance, no issues).

Expected payslip behaviour
--------------------------
**Vacation payslip** (auto-generated on GM Final Approval):
  - Covers the full month (April 1–30).
  - Attendance only exists for April 1–10 (10 days), so 20 calendar
    days are "unpresented / absent" → attendance deduction for 20 days.
  - Full monthly allowances fire: BASIC, HRA, Travel, Meal, Medical.
  - VACATION_BAL input = 5 days × daily_wage.
  - NET = full_gross − att_deduction_20_days − GOSI + VACATION_BAL.

**Monthly payslip** (batch-generated 1 May):
  - Covers the full month (April 1–30) for salary rules.
  - Attendance is only counted FROM the return date (April 16).
  - 15 worked days (Apr 16-30, all attended).
  - 15 absent days (Apr 1-15, pre-return period already covered by vac
    payslip).  ATTDED deducts daily_rate × 15.
  - PRIOR_HRA injected → HRA = 0 on this slip.
  - PRIOR_GOSI injected → GOSI = 0 on this slip (already paid in full).
  - NET = full_gross_without_HRA − att_deduction_15_days.

Employee setup
--------------
wage=6000  hra=1500  da=0  travel=500  meal=300  medical=200  other=0
  daily_rate = (6000 + 500 + 300 + 200) / 30 = 233.33…
  GOSI_full  = -round((6000 + 1500) × 9.75%) = -731
  GOSI_adj   = 0 (GOSI paid only once per month)
"""
from datetime import date, datetime, time as dt_time, timedelta

from odoo.tests.common import TransactionCase


class TestVacationMonthlyOverlap(TransactionCase):
    """Verify the full vacation + monthly payslip overlap scenario."""

    # ==================================================================
    # SETUP
    # ==================================================================

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Overlap Test Group',
        })
        for day in ['0', '1', '2', '3', '4', '5', '6']:
            # Every day of the week to keep calendar-day math simple
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Overlap Test Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Users for approval chain ──
        cls.user_dm = cls.env['res.users'].create({
            'name': 'DM Overlap', 'login': 'dm_overlap',
            'email': 'dm_o@test.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_dm = cls.env['hr.employee'].create({
            'name': 'DM Employee Overlap', 'user_id': cls.user_dm.id,
        })

        cls.user_hr = cls.env['res.users'].create({
            'name': 'HR Overlap', 'login': 'hr_overlap',
            'email': 'hr_o@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('hr_holidays.group_hr_holidays_user').id,
            ])],
        })
        cls.emp_hr = cls.env['hr.employee'].create({
            'name': 'HR Employee Overlap', 'user_id': cls.user_hr.id,
        })

        cls.user_gm = cls.env['res.users'].create({
            'name': 'GM Overlap', 'login': 'gm_overlap',
            'email': 'gm_o@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_gm').id,
            ])],
        })
        cls.emp_gm = cls.env['hr.employee'].create({
            'name': 'GM Employee Overlap', 'user_id': cls.user_gm.id,
        })

        cls.user_acc = cls.env['res.users'].create({
            'name': 'ACC Overlap', 'login': 'acc_overlap',
            'email': 'acc_o@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_acc').id,
            ])],
        })
        cls.emp_acc = cls.env['hr.employee'].create({
            'name': 'ACC Employee Overlap', 'user_id': cls.user_acc.id,
        })

        # ── Employee ──
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Overlap Test Employee',
            'resource_calendar_id': cls.calendar.id,
            'leave_manager_id': cls.user_dm.id,
            'country_id': cls.env.ref('base.sa').id,  # Saudi → GOSI
        })

        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Overlap Test Version',
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
            'name': 'Annual Leave Overlap Test',
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
        # When a prior payslip already paid GOSI, monthly gets 0
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

    def _approve_full_chain(self, leave, penalty=0, ticket=0):
        """Run the full 5-step approval chain."""
        # Step 1: DM
        leave.with_user(self.user_dm).sudo().action_dm_approve()
        # Step 2: HR (fill penalty)
        if penalty:
            leave.sudo().write({'x_penalty_amount': penalty})
        leave.with_user(self.user_hr).sudo().action_hr_approve()
        # Step 3: GM Initial
        leave.with_user(self.user_gm).sudo().action_gm_initial_approve()
        # Step 4: Accounting (fill flight ticket)
        if ticket:
            leave.sudo().write({'x_flight_ticket_amount': ticket})
        leave.with_user(self.user_acc).sudo().action_acc_approve()
        # Step 5: GM Final — this creates the vacation payslip
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

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
        """Return the salary line for a given code, or False."""
        return payslip.line_ids.filtered(lambda l: l.code == code)[:1]

    def _get_total(self, payslip, code):
        """Return the total of a salary line code, or 0."""
        line = self._get_line(payslip, code)
        return line.total if line else 0.0

    def _get_input(self, payslip, code):
        """Return the input line for a given code, or False."""
        return payslip.input_line_ids.filtered(lambda i: i.code == code)[:1]

    def _get_wd(self, payslip, code):
        """Return the worked-day line for a given code, or False."""
        return payslip.worked_days_line_ids.filtered(
            lambda w: w.code == code)[:1]

    # ==================================================================
    # THE MAIN END-TO-END TEST
    # ==================================================================

    def test_full_scenario_vacation_then_monthly(self):
        """
        Full scenario:
        1. Employee works April 1–10 (10 days).
        2. Annual leave approved April 11–15 → vacation payslip created.
        3. Employee returns April 16, confirmed.
        4. Employee works April 16–30 (15 days).
        5. Monthly payslip generated → covers full month but:
           - Attendance only counted from return date (Apr 16).
           - 15 worked days (Apr 16-30).
           - 15 absent days (Apr 1-15, pre-return period).
           - ATTDED deducts for 15 absent days.
           - PRIOR_HRA injected → HRA = 0 (already paid).
           - GOSI uses adjusted (zero) HRA base.

        Verifies:
        - Vacation payslip has correct worked days, HRA, VACATION_BAL.
        - Monthly payslip has correct worked/absent days, ATTDED, NO HRA.
        - GOSI is adjusted on the monthly payslip.
        - The combined total across both payslips is correct.
        """
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # ── 1. Create attendance for April 1–10 ──
        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        # ── 2. Create & approve annual leave April 11–15 ──
        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave, penalty=0, ticket=0)

        # Verify leave is approved and vacation payslip was created
        self.assertEqual(leave.state, 'validate')
        self.assertEqual(leave.x_return_state, 'on_vacation')

        vac_slip = leave.x_vacation_payslip_id
        self.assertTrue(vac_slip, 'Vacation payslip should have been created.')

        # ── 3. Confirm return (April 16) ──
        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        self.assertEqual(leave.x_return_state, 'manager_confirmed')

        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()
        self.assertEqual(leave.x_return_state, 'hr_confirmed')

        # ── 4. Create attendance for April 16–30 ──
        for d in range(16, 31):
            self._create_attendance(date(2026, 4, d))

        # ── 5. Verify vacation payslip details ──
        # The vacation payslip was computed during approval (April 1–30).
        # At that time, only April 1–10 attendance existed.

        # Worked days: 10 worked, 20 unpresented (absent)
        vac_work = self._get_wd(vac_slip, 'WORK100')
        self.assertTrue(vac_work, 'Vacation payslip should have WORK100 line.')
        self.assertEqual(vac_work.number_of_days, 10,
                         'Vacation payslip should show 10 worked days.')

        vac_absent = self._get_wd(vac_slip, 'ATT_ABS')
        if vac_absent:
            self.assertEqual(vac_absent.number_of_days, 20,
                             'Vacation payslip: 30 - 10 = 20 absent/unpresented days.')

        # Salary lines
        vac_basic = self._get_total(vac_slip, 'BASIC')
        self.assertEqual(vac_basic, 6000.0, 'Vacation payslip BASIC = 6000.')

        vac_hra = self._get_total(vac_slip, 'HRA')
        self.assertEqual(vac_hra, 1500.0, 'Vacation payslip HRA = 1500 (full).')

        # VACATION_BAL input should exist (5 days × wage/30)
        vac_bal_input = self._get_input(vac_slip, 'VACATION_BAL')
        if vac_bal_input:
            # 5 calendar days × (6000/30) = 5 × 200 = 1000
            expected_vac_bal = 5 * (self.WAGE / 30.0)
            self.assertAlmostEqual(
                vac_bal_input.amount, expected_vac_bal, places=0,
                msg='VACATION_BAL should be 5 days × daily basic wage.')

        # GOSI on vacation payslip
        vac_gosi = self._get_total(vac_slip, 'GOSI')
        self.assertEqual(vac_gosi, self.GOSI_FULL,
                         'Vacation payslip GOSI should use full basic+hra.')

        # Attendance deduction for 20 absent days
        vac_att_ded = self._get_total(vac_slip, 'ATTDED')
        expected_vac_ded = -round(self.DAILY_RATE * 20)
        self.assertEqual(vac_att_ded, expected_vac_ded,
                         'Vacation payslip ATTDED = -(daily_rate × 20 absent days).')

        # ── 6. Confirm vacation payslip (so it becomes "prior") ──
        vac_slip.action_payslip_done()
        self.assertEqual(vac_slip.state, 'done')

        # ── 7. Create and compute the monthly payslip ──
        monthly = self._create_monthly_payslip(month_start, month_end,
                                               name='April Monthly')
        monthly.compute_sheet()

        # ── 8. Verify monthly payslip details ──

        # The monthly payslip only counts attendance from the return date
        # (Apr 16) onwards — pre-vacation attendance is NOT double-counted.
        # Worked: 15 days (Apr 16-30, all attended)
        # Absent: 15 days (Apr 1-15, pre-return period covered by vac slip)
        # Salary rules fire at full-month amounts, so ATTDED must deduct
        # for the 15 pre-return absent days.
        m_work = self._get_wd(monthly, 'WORK100')
        self.assertTrue(m_work, 'Monthly payslip should have WORK100 line.')
        self.assertEqual(m_work.number_of_days, 15,
                         'Monthly payslip should show 15 worked days '
                         '(Apr 16-30, from return date onwards).')

        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent,
                        'Monthly payslip should have ATT_ABS line '
                        'for the 15 pre-return days.')
        self.assertEqual(m_absent.number_of_days, 15,
                         'Monthly payslip should show 15 absent days '
                         '(Apr 1-15, pre-return period).')

        # Verify ATT_ABS deduction amount = daily_rate × 15
        expected_absent_deduction = round(self.DAILY_RATE * 15)
        self.assertEqual(m_absent.amount, expected_absent_deduction,
                         'ATT_ABS deduction amount should be '
                         'daily_rate × 15 pre-return days.')

        # PRIOR_HRA injected
        prior_hra_input = self._get_input(monthly, 'PRIOR_HRA')
        self.assertTrue(prior_hra_input,
                        'Monthly payslip should have PRIOR_HRA input.')
        self.assertEqual(prior_hra_input.amount, 1500.0,
                         'PRIOR_HRA amount should be 1500.')

        # HRA = 0 (already paid in vacation payslip)
        m_hra = self._get_total(monthly, 'HRA')
        self.assertEqual(m_hra, 0.0,
                         'Monthly payslip HRA should be 0 (already paid).')

        # BASIC still full (deduction handled via ATTDED, not BASIC)
        m_basic = self._get_total(monthly, 'BASIC')
        self.assertEqual(m_basic, 6000.0, 'Monthly payslip BASIC = 6000.')

        # ATTDED = -(daily_rate × 15 absent days)
        m_att_ded = self._get_total(monthly, 'ATTDED')
        expected_monthly_ded = -round(self.DAILY_RATE * 15)
        self.assertEqual(m_att_ded, expected_monthly_ded,
                         'Monthly payslip ATTDED should deduct for '
                         '15 pre-return absent days.')

        # GOSI on monthly payslip = 0 (already fully paid on vacation payslip)
        m_gosi = self._get_total(monthly, 'GOSI')
        self.assertEqual(m_gosi, 0.0,
                         'Monthly payslip GOSI should be 0 (already paid in full).')

        # No VACATION_BAL on monthly payslip
        m_vac_bal = self._get_input(monthly, 'VACATION_BAL')
        self.assertFalse(m_vac_bal,
                         'Monthly payslip should NOT have VACATION_BAL input.')

        # ── 9. Verify HRA paid exactly once ──
        total_hra = self._get_total(vac_slip, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0,
                         'HRA should be paid exactly once across both payslips.')

    def test_monthly_payslip_without_prior_vacation(self):
        """When no vacation payslip exists, monthly gets full HRA."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # Attendance for all 30 days
        for d in range(1, 31):
            self._create_attendance(date(2026, 4, d))

        slip = self._create_monthly_payslip(month_start, month_end,
                                            name='Full Month')
        slip.compute_sheet()

        # HRA should be full
        hra = self._get_total(slip, 'HRA')
        self.assertEqual(hra, 1500.0, 'Full month payslip HRA = 1500.')

        # No PRIOR_HRA
        prior = self._get_input(slip, 'PRIOR_HRA')
        self.assertFalse(prior, 'No PRIOR_HRA when no prior payslip.')

        # 30 worked days, 0 absent
        work = self._get_wd(slip, 'WORK100')
        self.assertEqual(work.number_of_days, 30)

        absent = self._get_wd(slip, 'ATT_ABS')
        self.assertFalse(absent, 'No absent days when fully attended.')

    def test_vacation_payslip_recompute_after_return(self):
        """Vacation payslip can be recomputed without the vacation guard
        blocking it (since x_vacation_payslip_id is set on the leave)."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # Attendance April 1–10
        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        # Approve leave April 11–15
        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)

        vac_slip = leave.x_vacation_payslip_id
        self.assertTrue(vac_slip)

        # Confirm return
        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()
        self.assertEqual(leave.x_return_state, 'hr_confirmed')

        # Recompute vacation payslip — should NOT raise
        vac_slip.compute_sheet()

        # Verify it still has correct data
        vac_hra = self._get_total(vac_slip, 'HRA')
        self.assertEqual(vac_hra, 1500.0)

    def test_unconfirmed_return_blocks_monthly_payslip(self):
        """If return is not HR-confirmed, monthly payslip computation
        should be blocked by the vacation guard."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # Attendance April 1–10
        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        # Approve leave → on_vacation
        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)
        self.assertEqual(leave.x_return_state, 'on_vacation')

        # Don't confirm return → monthly payslip should be blocked
        monthly = self._create_monthly_payslip(month_start, month_end)
        blocked = False
        try:
            monthly.compute_sheet()
        except Exception:
            blocked = True
        self.assertTrue(blocked,
                        'Monthly payslip should be blocked when vacation '
                        'return is not confirmed.')

    def test_manager_only_confirmed_still_blocks(self):
        """If only DM confirmed return (not HR), monthly is still blocked."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)

        # Only DM confirms return
        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        self.assertEqual(leave.x_return_state, 'manager_confirmed')

        monthly = self._create_monthly_payslip(month_start, month_end)
        blocked = False
        try:
            monthly.compute_sheet()
        except Exception:
            blocked = True
        self.assertTrue(blocked,
                        'Monthly payslip should be blocked when only '
                        'manager confirmed return (HR not yet).')

    def test_combined_net_is_reasonable(self):
        """The combined NET from vacation + monthly payslips should be
        reasonable. HRA paid only once."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # Attendance April 1–10
        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        # Approve leave April 11–15
        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        # Confirm return
        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        # Attendance April 16–30
        for d in range(16, 31):
            self._create_attendance(date(2026, 4, d))

        # Confirm vacation payslip
        vac_slip.action_payslip_done()

        # Monthly payslip
        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        vac_net = self._get_total(vac_slip, 'NET')
        m_net = self._get_total(monthly, 'NET')
        combined = vac_net + m_net

        # The combined NET should be positive and reasonable
        self.assertGreater(combined, 5000,
                           'Combined NET should be at least 5000 for this salary.')
        self.assertLess(combined, 15000,
                        'Combined NET should not exceed 15000 (single month salary).')

        # HRA should only appear once across both payslips
        total_hra = self._get_total(vac_slip, 'HRA') + self._get_total(monthly, 'HRA')
        self.assertEqual(total_hra, 1500.0,
                         'HRA should be paid exactly once across both payslips.')

    def test_flight_ticket_and_penalty_in_vacation_payslip(self):
        """Flight ticket and penalty should only appear on vacation payslip,
        not on the monthly payslip."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave, penalty=500, ticket=2000)

        vac_slip = leave.x_vacation_payslip_id
        self.assertTrue(vac_slip)

        # Verify inputs on vacation payslip
        penalty_input = self._get_input(vac_slip, 'PENALTY')
        self.assertTrue(penalty_input)
        self.assertEqual(penalty_input.amount, 500.0)

        ticket_input = self._get_input(vac_slip, 'FLIGHT_TICKET')
        self.assertTrue(ticket_input)
        self.assertEqual(ticket_input.amount, 2000.0)

        # Verify salary lines
        penalty_line = self._get_total(vac_slip, 'PENALTY')
        self.assertEqual(penalty_line, -500.0,
                         'PENALTY should be -500 deduction.')

        ticket_line = self._get_total(vac_slip, 'FLIGHT_TICKET')
        self.assertEqual(ticket_line, 2000.0,
                         'FLIGHT_TICKET should be 2000 allowance.')

        # Confirm and create monthly
        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        for d in range(16, 31):
            self._create_attendance(date(2026, 4, d))

        vac_slip.action_payslip_done()

        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        # Monthly should NOT have PENALTY or FLIGHT_TICKET
        m_penalty = self._get_input(monthly, 'PENALTY')
        self.assertFalse(m_penalty,
                         'Monthly payslip should NOT have PENALTY input.')

        m_ticket = self._get_input(monthly, 'FLIGHT_TICKET')
        self.assertFalse(m_ticket,
                         'Monthly payslip should NOT have FLIGHT_TICKET input.')

    # ==================================================================
    # PRE-RETURN ABSENT DAY TESTS
    # ==================================================================

    def test_pre_return_absent_deduction_exact_amount(self):
        """Verify the exact ATT_ABS deduction amount for the pre-return
        period.  daily_rate = (6000+500+300+200)/30 ≈ 233.33.
        15 absent days → deduction = round(233.33×15) = 3500."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        for d in range(16, 31):
            self._create_attendance(date(2026, 4, d))

        vac_slip.action_payslip_done()

        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent, 'ATT_ABS line must exist.')
        self.assertEqual(m_absent.number_of_days, 15)
        expected_ded = round(self.DAILY_RATE * 15)
        self.assertEqual(m_absent.amount, expected_ded,
                         f'ATT_ABS amount should be {expected_ded}.')

        # ATT_DED worked-day line should also exist
        m_att_ded_wd = self._get_wd(monthly, 'ATT_DED')
        self.assertTrue(m_att_ded_wd,
                        'ATT_DED worked-day line must exist.')
        self.assertEqual(m_att_ded_wd.number_of_days, 15)
        self.assertEqual(m_att_ded_wd.amount, expected_ded)

    def test_partial_attendance_after_return(self):
        """Employee returns Apr 16 but misses Apr 20 and Apr 25.
        Monthly payslip should have:
        - 13 worked days (15 post-return - 2 missed)
        - 17 absent days (15 pre-return + 2 missed after return)
        - ATTDED for 17 absent days."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        # Attend Apr 16-30 except Apr 20 and Apr 25
        for d in range(16, 31):
            if d not in (20, 25):
                self._create_attendance(date(2026, 4, d))

        vac_slip.action_payslip_done()

        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        m_work = self._get_wd(monthly, 'WORK100')
        self.assertTrue(m_work)
        self.assertEqual(m_work.number_of_days, 13,
                         'Should have 13 worked days (15 post-return minus '
                         '2 missed).')

        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        # 15 pre-return + 2 missed = 17 absent days
        self.assertEqual(m_absent.number_of_days, 17,
                         'Should have 17 absent days (15 pre-return + '
                         '2 missed after return).')

        # ATTDED should deduct for all 17 absent days
        m_att_ded = self._get_total(monthly, 'ATTDED')
        expected_ded = -round(self.DAILY_RATE * 17)
        self.assertEqual(m_att_ded, expected_ded,
                         f'ATTDED should be {expected_ded} for 17 absent days.')

    def test_late_return_date_most_of_month_absent(self):
        """Employee returns Apr 26 (only 5 days of work on monthly).
        Pre-return absent = 25 days.  Total absent = 25."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # Only 3 days of pre-vacation attendance
        for d in range(1, 4):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 4), date(2026, 4, 25))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        leave.sudo().write({'x_return_date': date(2026, 4, 26)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        # Only 5 days after return
        for d in range(26, 31):
            self._create_attendance(date(2026, 4, d))

        vac_slip.action_payslip_done()

        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        m_work = self._get_wd(monthly, 'WORK100')
        self.assertEqual(m_work.number_of_days, 5,
                         'Only 5 days worked after late return.')

        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        self.assertEqual(m_absent.number_of_days, 25,
                         'Should have 25 pre-return absent days.')

        m_att_ded = self._get_total(monthly, 'ATTDED')
        expected_ded = -round(self.DAILY_RATE * 25)
        self.assertEqual(m_att_ded, expected_ded,
                         f'ATTDED should be {expected_ded} for 25 absent days.')

    def test_early_return_date_minimal_absence(self):
        """Employee takes short 2-day leave (Apr 3-4), returns Apr 5.
        Pre-return absent = 4 days (Apr 1-4)."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # Pre-vacation attendance: Apr 1-2
        for d in range(1, 3):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 3), date(2026, 4, 4))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        leave.sudo().write({'x_return_date': date(2026, 4, 5)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        # Post-return attendance: Apr 5-30 = 26 days
        for d in range(5, 31):
            self._create_attendance(date(2026, 4, d))

        vac_slip.action_payslip_done()

        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        m_work = self._get_wd(monthly, 'WORK100')
        self.assertEqual(m_work.number_of_days, 26,
                         'Should have 26 worked days after early return.')

        m_absent = self._get_wd(monthly, 'ATT_ABS')
        self.assertTrue(m_absent)
        # Pre-return = (Apr 5 - Apr 1).days = 4 days
        self.assertEqual(m_absent.number_of_days, 4,
                         'Should have 4 pre-return absent days (Apr 1-4).')

        m_att_ded = self._get_total(monthly, 'ATTDED')
        expected_ded = -round(self.DAILY_RATE * 4)
        self.assertEqual(m_att_ded, expected_ded)

    def test_combined_net_close_to_single_month(self):
        """Combined NET from vacation + monthly should be close to a normal
        full-month NET + vacation balance.

        Full-month NET (no vacation) ≈ 8500 - 731 = 7769.
        With vacation (GOSI paid once on vacation payslip, 0 on monthly):
          vac_net  ≈ 8500 - round(233.33×20) + 1000 - 731 = 4102
          mon_net  ≈ 7000 - round(233.33×15)               = 3500
          combined ≈ 7602
        """
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        for d in range(16, 31):
            self._create_attendance(date(2026, 4, d))

        vac_slip.action_payslip_done()

        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        vac_net = self._get_total(vac_slip, 'NET')
        m_net = self._get_total(monthly, 'NET')
        combined = vac_net + m_net

        # The combined NET should not be more than a normal month + vac balance
        normal_net = (self.WAGE + self.HRA + self.TRAVEL + self.MEAL
                      + self.MEDICAL + self.GOSI_FULL)  # 8500 - 731 = 7769
        vac_bal = 5 * (self.WAGE / 30.0)  # 1000
        max_reasonable = normal_net + vac_bal  # 8769

        self.assertLessEqual(
            combined, max_reasonable + 100,
            f'Combined NET {combined} should not exceed normal month '
            f'+ vacation balance ({max_reasonable}).')

        # Should also not be too low — employee worked full month
        self.assertGreater(combined, 5000,
                           'Combined NET should be at least 5000.')

    def test_monthly_without_vacation_no_pre_return_absent(self):
        """When no vacation return exists, there should be no pre-return
        absent days — the full month attendance is counted normally."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        # Full 30 days of attendance
        for d in range(1, 31):
            self._create_attendance(date(2026, 4, d))

        slip = self._create_monthly_payslip(month_start, month_end,
                                            name='Full Month No Vacation')
        slip.compute_sheet()

        work = self._get_wd(slip, 'WORK100')
        self.assertEqual(work.number_of_days, 30)

        absent = self._get_wd(slip, 'ATT_ABS')
        self.assertFalse(absent, 'No absent days without vacation.')

        att_ded = self._get_total(slip, 'ATTDED')
        self.assertEqual(att_ded, 0.0, 'No ATTDED without absent days.')

    def test_vacation_payslip_not_affected_by_pre_return_logic(self):
        """The vacation payslip itself should NOT get pre-return absent
        days injected — only the monthly payslip does."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        # Recompute the vacation payslip
        vac_slip.compute_sheet()

        # Vacation payslip should still count from payslip start (Apr 1)
        vac_work = self._get_wd(vac_slip, 'WORK100')
        self.assertTrue(vac_work)
        self.assertEqual(vac_work.number_of_days, 10,
                         'Vacation payslip should show 10 worked days '
                         '(Apr 1-10, NOT affected by return-date logic).')

        vac_absent = self._get_wd(vac_slip, 'ATT_ABS')
        if vac_absent:
            self.assertEqual(vac_absent.number_of_days, 20,
                             'Vacation payslip should show 20 absent days '
                             '(NOT affected by pre-return logic).')

    def test_att_ded_worked_day_line_matches_attded_salary_rule(self):
        """The ATT_DED worked-day line amount should produce a matching
        ATTDED salary rule output (negative deduction)."""
        month_start = date(2026, 4, 1)
        month_end = date(2026, 4, 30)

        for d in range(1, 11):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 11), date(2026, 4, 15))
        self._approve_full_chain(leave)
        vac_slip = leave.x_vacation_payslip_id

        leave.sudo().write({'x_return_date': date(2026, 4, 16)})
        leave.sudo().action_confirm_return_manager()
        leave.with_user(self.user_hr).sudo().action_confirm_return_hr()

        for d in range(16, 31):
            self._create_attendance(date(2026, 4, d))

        vac_slip.action_payslip_done()

        monthly = self._create_monthly_payslip(month_start, month_end)
        monthly.compute_sheet()

        # ATT_DED worked-day amount
        att_ded_wd = self._get_wd(monthly, 'ATT_DED')
        self.assertTrue(att_ded_wd, 'ATT_DED worked-day line must exist.')

        # ATTDED salary rule line — should be negative of the WD amount
        attded_salary = self._get_total(monthly, 'ATTDED')
        self.assertEqual(attded_salary, -att_ded_wd.amount,
                         'ATTDED salary rule should be -ATT_DED worked-day amount.')













