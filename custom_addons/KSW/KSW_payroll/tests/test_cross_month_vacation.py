# -*- coding: utf-8 -*-
"""Cross-month annual vacation payslip tests.

Validates that when an employee's annual vacation spans multiple calendar
months, only ONE vacation payslip is created for the **current month**
(the month the leave is approved).  Past months are already settled via
regular monthly payslip batches; future months will be handled by
upcoming batches.

Key rule: the vacation payslip is always for the current month (today's
month), regardless of when the leave starts or ends.

Scenarios
---------
S1: Leave starts in the past (Feb 2025 – Apr 2026).
    Vacation payslip covers April 2026 (current month), not Feb 2025.

S2: Leave starts this month (Apr 5 – Apr 12).
    Same-month single-month case — payslip for April.

S3: Leave starts this month, ends next month (Apr 20 – May 10).
    Payslip for April (current month). May handled by monthly batch.

S4: Leave starts in March, ends in April (Mar 20 – Apr 15).
    Payslip for April (current month). March already settled.

S5: Same-month vacation with monthly payslip overlap.
    Vacation payslip + monthly payslip both in April. PRIOR_HRA.

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

        # The current month when tests run (used for assertions)
        cls.TODAY = date.today()
        cls.CURRENT_MONTH_START = cls.TODAY.replace(day=1)

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
    # S1: Leave in the past — payslip should still be current month
    # ==================================================================

    def test_s1_past_leave_payslip_is_current_month(self):
        """
        S1 — Leave started in the past (Mar 15 – Apr 22).
        The vacation payslip should cover the current month (April),
        NOT March.  March is already settled.
        """
        # Remove any mandatory days / public holidays that might conflict
        self.env.cr.execute("""
            DELETE FROM resource_calendar_leaves
            WHERE resource_id IS NULL
        """)
        self.env.cr.execute("""
            DELETE FROM hr_leave_mandatory_day
        """)
        self.env.invalidate_all()

        # Pre-vacation attendance — current month up to today
        for d in range(1, self.TODAY.day):
            self._create_attendance(date(self.TODAY.year, self.TODAY.month, d))

        leave = self._create_leave_sql(date(2026, 3, 15), date(2026, 4, 22))
        self._approve_full_chain(leave)
        self.assertEqual(leave.state, 'validate')

        # ONE vacation payslip — for current month
        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 1,
                         'S1: Only one vacation payslip.')

        vac = vac_payslips[0]
        self.assertEqual(vac.date_from.month, self.TODAY.month,
                         'S1: Payslip is for current month, not leave start.')
        self.assertEqual(vac.date_from.year, self.TODAY.year)
        self.assertEqual(vac.date_from.day, 1,
                         'S1: Payslip starts on the 1st.')

        # Has VACATION_BAL and allowances
        self.assertTrue(self._get_input(vac, 'VACATION_BAL'))
        self.assertEqual(self._get_total(vac, 'HRA'), 1500.0)
        self.assertEqual(self._get_total(vac, 'GOSI'), self.GOSI_FULL)

    # ==================================================================
    # S2: Same-month leave — payslip is also current month
    # ==================================================================

    def test_s2_same_month_leave(self):
        """
        S2 — Leave within the current month (Apr 5 – Apr 12).
        Payslip should be for April (current month).
        """
        for d in range(1, 5):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 5), date(2026, 4, 12))
        self._approve_full_chain(leave)

        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 1)
        vac = vac_payslips[0]
        self.assertEqual(vac.date_from, date(2026, 4, 1))
        self.assertEqual(vac.date_to, date(2026, 4, 30))
        self.assertTrue(self._get_input(vac, 'VACATION_BAL'))

        # Confirm return and test monthly payslip
        self._confirm_return(leave, date(2026, 4, 13))
        for d in range(13, 31):
            self._create_attendance(date(2026, 4, d))
        vac.action_payslip_done()

        monthly = self._create_monthly_payslip(
            date(2026, 4, 1), date(2026, 4, 30), name='S2 Monthly')
        monthly.compute_sheet()

        # PRIOR_HRA — same month overlap
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0)
        self.assertEqual(self._get_wd(monthly, 'WORK100').number_of_days, 18)
        self.assertEqual(self._get_wd(monthly, 'ATT_ABS').number_of_days, 12)

    # ==================================================================
    # S3: Leave starts this month, ends next month
    # ==================================================================

    def test_s3_current_to_next_month(self):
        """
        S3 — Leave from Apr 20 – May 10.
        Payslip for April (current month). May handled by monthly batch.
        """
        for d in range(1, 20):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 4, 20), date(2026, 5, 10))
        self._approve_full_chain(leave)

        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 1)
        vac = vac_payslips[0]
        self.assertEqual(vac.date_from, date(2026, 4, 1),
                         'S3: Payslip is for current month (April).')
        self.assertTrue(self._get_input(vac, 'VACATION_BAL'))
        self.assertEqual(self._get_total(vac, 'HRA'), 1500.0)
        self.assertEqual(self._get_total(vac, 'GOSI'), self.GOSI_FULL)

    # ==================================================================
    # S4: Leave started last month, extends into current month
    # ==================================================================

    def test_s4_past_start_current_end(self):
        """
        S4 — Leave Mar 20 – Apr 15.
        Payslip for April (current month), not March.
        After return, April monthly payslip gets PRIOR_HRA from the
        April vacation payslip.
        """
        for d in range(1, self.TODAY.day):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 3, 20), date(2026, 4, 15))
        self._approve_full_chain(leave)

        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 1)
        vac = vac_payslips[0]
        self.assertEqual(vac.date_from, date(2026, 4, 1),
                         'S4: Payslip is for current month (April).')
        self.assertTrue(self._get_input(vac, 'VACATION_BAL'))

        # Confirm return, create attendance, make monthly payslip
        self._confirm_return(leave, date(2026, 4, 20))
        for d in range(20, 31):
            self._create_attendance(date(2026, 4, d))
        vac.action_payslip_done()

        monthly = self._create_monthly_payslip(
            date(2026, 4, 1), date(2026, 4, 30), name='S4 Monthly')
        monthly.compute_sheet()

        # PRIOR_HRA — vacation payslip is also for April
        prior = self._get_input(monthly, 'PRIOR_HRA')
        self.assertTrue(prior, 'S4: PRIOR_HRA injected (same month).')
        self.assertEqual(prior.amount, 1500.0)
        self.assertEqual(self._get_total(monthly, 'HRA'), 0.0)
        self.assertEqual(self._get_total(monthly, 'GOSI'), 0.0)

    # ==================================================================
    # S5: Future-month leave — payslip still current month
    # ==================================================================

    def test_s5_future_leave_payslip_is_current_month(self):
        """
        S5 — Leave entirely in the future (May 1 – May 15).
        Payslip is still for the current month (April) — the employee
        is getting their salary for the current month before going
        on vacation.
        """
        # Full April attendance up to today
        for d in range(1, self.TODAY.day):
            self._create_attendance(date(2026, 4, d))

        leave = self._create_leave_sql(date(2026, 5, 1), date(2026, 5, 15))
        self._approve_full_chain(leave)

        vac_payslips = leave.x_vacation_payslip_ids
        self.assertEqual(len(vac_payslips), 1)
        vac = vac_payslips[0]
        self.assertEqual(vac.date_from, date(2026, 4, 1),
                         'S5: Payslip is for current month even for future leave.')
        self.assertTrue(self._get_input(vac, 'VACATION_BAL'))
        self.assertEqual(self._get_total(vac, 'HRA'), 1500.0)
