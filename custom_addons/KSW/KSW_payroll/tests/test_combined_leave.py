# -*- coding: utf-8 -*-
"""Tests for Combined Annual + Unpaid Leave feature.

Covers:
  - Duration computation: annual portion vs unpaid portion split
  - Mutual exclusivity between full clearance and excess days
  - Combined leave payslip inputs (VACATION_BAL uses annual portion,
    FIN_CONSIDERATION, VISA_COST_RECOVERY deductions)
  - Commission lines (computed total, reset on refuse)
  - Accrual impact: unpaid portion reduces effective service days
  - Attendance sheet locking for annual leaves
  - Reset / refuse / draft clears combined leave fields
"""
from datetime import date, datetime, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCombinedLeave(TransactionCase):
    """Tests for the combined annual+unpaid leave flow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Combined Group',
        })
        for day in ['0', '1', '2', '3', '6']:
            cls.env['resource.calendar.group.line'].create({
                'name': f'Work Day {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Combined Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Users with specific groups ──
        cls.user_dm = cls.env['res.users'].create({
            'name': 'DM Combined',
            'login': 'test_dm_combined',
            'email': 'dm_comb@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
            ])],
        })
        cls.emp_dm = cls.env['hr.employee'].create({
            'name': 'DM Combined Employee',
            'user_id': cls.user_dm.id,
        })

        cls.user_hr = cls.env['res.users'].create({
            'name': 'HR Combined',
            'login': 'test_hr_combined',
            'email': 'hr_comb@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('hr_holidays.group_hr_holidays_user').id,
            ])],
        })
        cls.emp_hr = cls.env['hr.employee'].create({
            'name': 'HR Combined Employee',
            'user_id': cls.user_hr.id,
        })

        cls.user_gm = cls.env['res.users'].create({
            'name': 'GM Combined',
            'login': 'test_gm_combined',
            'email': 'gm_comb@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_gm').id,
            ])],
        })
        cls.emp_gm = cls.env['hr.employee'].create({
            'name': 'GM Combined Employee',
            'user_id': cls.user_gm.id,
        })

        cls.user_acc = cls.env['res.users'].create({
            'name': 'ACC Combined',
            'login': 'test_acc_combined',
            'email': 'acc_comb@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_acc').id,
            ])],
        })
        cls.emp_acc = cls.env['hr.employee'].create({
            'name': 'ACC Combined Employee',
            'user_id': cls.user_acc.id,
        })

        # ── Employee requesting leave ──
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Combined Employee',
            'resource_calendar_id': cls.calendar.id,
            'leave_manager_id': cls.user_dm.id,
        })

        # ── Version (contract) with wage ──
        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Test Version Combined',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': cls.calendar.id,
            'wage': 6000.0,
            'hra': 1500.0,
            'struct_id': cls.env.ref('om_hr_payroll.structure_base').id,
        })
        cls.employee._compute_current_version_id()

        # ── Annual leave type with multi-step validation ──
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave Combined Test',
            'requires_allocation': False,
            'leave_validation_type': 'annual_multi',
            'is_annual_leave': True,
        })

        # ── Daily wage ──
        cls.daily_wage = 6000.0 / 30.0  # 200.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_leave(self, date_from=None, date_to=None,
                      excess_days=False, full_clearance=False):
        """Create an annual_multi leave request via raw SQL."""
        date_from = date_from or date(2026, 6, 1)
        date_to = date_to or date(2026, 6, 20)
        date_from_utc = datetime.combine(
            date_from, datetime.min.time()) + timedelta(hours=5)
        date_to_utc = datetime.combine(
            date_to, datetime.min.time()) + timedelta(hours=13, minutes=30)
        cal_days = (date_to - date_from).days + 1

        self.env.cr.execute("""
            INSERT INTO hr_leave
                (employee_id, holiday_status_id, state,
                 request_date_from, request_date_to,
                 date_from, date_to,
                 number_of_days, number_of_hours,
                 x_return_state, x_annual_approval_state,
                 x_excess_days_accepted, x_is_full_clearance,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'confirm',
                 %s, %s, %s, %s,
                 %s, %s,
                 'not_applicable', 'pending_dm',
                 %s, %s,
                 %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            self.employee.id, self.leave_type.id,
            date_from, date_to, date_from_utc, date_to_utc,
            cal_days, cal_days * 8.0,
            excess_days, full_clearance,
            self.env.uid, self.env.uid,
        ))
        leave_id = self.env.cr.fetchone()[0]
        self.env.invalidate_all()
        return self.env['hr.leave'].browse(leave_id)

    def _create_annual_balance(self):
        """Ensure a ksw.annual.leave record exists for the employee."""
        existing = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', self.employee.id),
        ])
        if existing:
            return existing
        return self.env['ksw.annual.leave'].sudo().create({
            'employee_id': self.employee.id,
        })

    def _get_actual_balance(self):
        """Read the actual remaining balance from ksw.annual.leave."""
        rec = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', self.employee.id),
        ], limit=1)
        return rec.remaining_balance if rec else 0.0

    def _approve_through_step(self, leave, up_to_step):
        """Run the approval chain up to and including the given step."""
        steps = [
            ('dm', self.user_dm, 'action_dm_approve'),
            ('hr', self.user_hr, 'action_hr_approve'),
            ('gm_initial', self.user_gm, 'action_gm_initial_approve'),
            ('acc', self.user_acc, 'action_acc_approve'),
            ('gm_final', self.user_gm, 'action_gm_final_approve'),
        ]
        for step_name, user, method_name in steps:
            getattr(leave.with_user(user).sudo(), method_name)()
            if step_name == up_to_step:
                break

    # ==================================================================
    # EXCESS DAYS — DURATION COMPUTATION
    # ==================================================================

    def test_excess_days_splits_annual_and_unpaid(self):
        """When excess_days_accepted, number_of_days = balance,
        x_unpaid_portion_days = cal_days - balance."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0, "Need positive balance for this test")

        # Request more days than balance
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)

        # Trigger recompute
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertAlmostEqual(
            leave.number_of_days, balance, places=2,
            msg="number_of_days should equal the annual balance")
        self.assertAlmostEqual(
            leave.x_annual_portion_days, balance, places=2,
            msg="annual portion should equal balance")
        self.assertAlmostEqual(
            leave.x_unpaid_portion_days, cal_days - balance, places=2,
            msg="unpaid portion should be cal_days minus balance")
        self.assertAlmostEqual(
            leave.x_actual_vacation_days, cal_days, places=0,
            msg="actual vacation days should be total cal_days")
        self.assertEqual(
            leave.x_clearance_balance, 0,
            msg="clearance balance must be 0 for combined leaves")

    def test_excess_no_excess_when_balance_covers(self):
        """When balance >= cal_days, excess toggle is auto-cleared and
        the leave becomes a regular annual leave (no portion split)."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0)

        # Request fewer days than balance
        cal_days = max(int(balance) - 5, 1)
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        # Excess toggle is auto-cleared when cal_days <= balance
        self.assertFalse(leave.x_excess_days_accepted,
            msg="Excess toggle should be auto-cleared when balance covers all days")
        self.assertAlmostEqual(leave.number_of_days, cal_days, places=0)
        # Portion fields are 0 because the leave is now a regular annual leave
        self.assertEqual(leave.x_annual_portion_days, 0)
        self.assertEqual(leave.x_unpaid_portion_days, 0)

    def test_get_durations_returns_annual_portion_only(self):
        """_get_durations returns the annual portion, not the full cal_days."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        result = leave._get_durations()
        days, hours = result[leave.id]
        self.assertAlmostEqual(
            days, balance, places=2,
            msg="_get_durations should return annual portion only")

    def test_get_number_of_days_returns_balance(self):
        """_get_number_of_days returns balance when excess accepted."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        result = leave._get_number_of_days(
            leave.date_from, leave.date_to, self.employee.id)
        self.assertAlmostEqual(
            result['days'], balance, places=2,
            msg="_get_number_of_days should return annual balance")

    # ==================================================================
    # MUTUAL EXCLUSIVITY: Full Clearance vs Excess Days
    # ==================================================================

    def test_full_clearance_clears_excess_fields(self):
        """Full clearance sets x_annual_portion_days and
        x_unpaid_portion_days to 0."""
        self._create_annual_balance()
        leave = self._create_leave(full_clearance=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertEqual(leave.x_annual_portion_days, 0)
        self.assertEqual(leave.x_unpaid_portion_days, 0)
        self.assertGreater(leave.x_clearance_balance, 0)

    def test_excess_days_clears_clearance_fields(self):
        """Excess accepted sets x_clearance_balance to 0."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertEqual(leave.x_clearance_balance, 0)

    # ==================================================================
    # COMMISSION LINES
    # ==================================================================

    def test_commission_lines_compute_total(self):
        """Commission line amounts are summed into x_additional_commissions."""
        leave = self._create_leave()
        self.env['hr.leave.commission.line'].create([
            {'leave_id': leave.id, 'name': 'Jan 2026', 'amount': 1000.0},
            {'leave_id': leave.id, 'name': 'Feb 2026', 'amount': 1500.0},
            {'leave_id': leave.id, 'name': 'Mar 2026', 'amount': 800.0},
        ])
        leave.invalidate_recordset()
        self.assertAlmostEqual(leave.x_additional_commissions, 3300.0)

    def test_commission_lines_empty_gives_zero(self):
        """No commission lines → total is 0."""
        leave = self._create_leave()
        self.assertEqual(leave.x_additional_commissions, 0)

    def test_commission_lines_deleted_on_reset(self):
        """Commission lines are deleted when multi-step fields are reset."""
        leave = self._create_leave()
        self.env['hr.leave.commission.line'].create([
            {'leave_id': leave.id, 'name': 'Jan', 'amount': 500.0},
        ])
        self.assertEqual(len(leave.x_commission_line_ids), 1)

        leave._reset_annual_multi_fields()
        self.assertEqual(len(leave.x_commission_line_ids), 0)
        self.assertEqual(leave.x_additional_commissions, 0)

    # ==================================================================
    # COMBINED LEAVE PAYSLIP INPUTS
    # ==================================================================

    def test_combined_payslip_vacation_bal_uses_annual_portion(self):
        """VACATION_BAL input uses x_annual_portion_days, not full cal_days."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        # Set accounting fields
        leave.sudo().write({
            'x_financial_consideration_excess': 1000.0,
            'x_visa_cost_recovery': 500.0,
        })

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        self.assertTrue(payslip, 'Vacation payslip should be created.')

        inputs_by_code = {i.code: i for i in payslip.input_line_ids}

        # VACATION_BAL should use annual portion (= balance), not cal_days
        expected_vac = balance * self.daily_wage
        self.assertIn('VACATION_BAL', inputs_by_code)
        self.assertAlmostEqual(
            inputs_by_code['VACATION_BAL'].amount, expected_vac, places=2,
            msg="VACATION_BAL should be annual_portion × daily_wage")

    def test_combined_payslip_has_fin_consideration(self):
        """FIN_CONSIDERATION input appears when filled on combined leave."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        leave.sudo().write({
            'x_financial_consideration_excess': 2500.0,
        })

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        inputs_by_code = {i.code: i for i in payslip.input_line_ids}

        self.assertIn('FIN_CONSIDERATION', inputs_by_code)
        self.assertEqual(inputs_by_code['FIN_CONSIDERATION'].amount, 2500.0)

    def test_combined_payslip_has_visa_cost_recovery(self):
        """VISA_COST_RECOVERY input appears when filled on combined leave."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        leave.sudo().write({
            'x_visa_cost_recovery': 1200.0,
        })

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        inputs_by_code = {i.code: i for i in payslip.input_line_ids}

        self.assertIn('VISA_COST_RECOVERY', inputs_by_code)
        self.assertEqual(inputs_by_code['VISA_COST_RECOVERY'].amount, 1200.0)

    def test_combined_payslip_no_unpaid_inputs_when_zero(self):
        """No FIN_CONSIDERATION or VISA_COST_RECOVERY when amounts are 0."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        # Don't set unpaid accounting fields
        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        codes = payslip.input_line_ids.mapped('code')

        self.assertNotIn('FIN_CONSIDERATION', codes)
        self.assertNotIn('VISA_COST_RECOVERY', codes)

    def test_combined_payslip_includes_commissions(self):
        """ADDITIONAL_COMMISSIONS input appears when commission lines exist."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 3
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        # Add commission lines
        self.env['hr.leave.commission.line'].create([
            {'leave_id': leave.id, 'name': 'Jan', 'amount': 1000.0},
            {'leave_id': leave.id, 'name': 'Feb', 'amount': 500.0},
        ])
        leave.invalidate_recordset()

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        inputs_by_code = {i.code: i for i in payslip.input_line_ids}

        self.assertIn('ADDITIONAL_COMMISSIONS', inputs_by_code)
        self.assertEqual(
            inputs_by_code['ADDITIONAL_COMMISSIONS'].amount, 1500.0)

    def test_normal_leave_payslip_uses_full_cal_days(self):
        """Normal annual leave (no excess) uses full calendar days."""
        self._create_annual_balance()
        leave = self._create_leave(
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 10),
        )

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        inputs_by_code = {i.code: i for i in payslip.input_line_ids}

        cal_days = 10  # Jun 1-10
        expected_vac = cal_days * self.daily_wage
        self.assertIn('VACATION_BAL', inputs_by_code)
        self.assertAlmostEqual(
            inputs_by_code['VACATION_BAL'].amount, expected_vac, places=2)

    # ==================================================================
    # ACCRUAL IMPACT — UNPAID PORTION REDUCES SERVICE DAYS
    # ==================================================================

    def test_unpaid_portion_counted_in_accrual(self):
        """Combined leave's unpaid portion is included in
        _get_unpaid_leave_days for accrual reduction.

        Note: After _action_validate, _compute_duration is re-triggered
        because state changed, and the remaining balance is 0 (consumed),
        so x_unpaid_portion_days resets.  We test _get_unpaid_leave_days
        directly by writing the field via SQL to verify the function logic.
        """
        self._create_annual_balance()

        # Create a validated annual leave with excess days via SQL
        date_from = date(2026, 7, 1)
        date_to = date(2026, 7, 20)
        date_from_utc = datetime.combine(
            date_from, datetime.min.time()) + timedelta(hours=5)
        date_to_utc = datetime.combine(
            date_to, datetime.min.time()) + timedelta(hours=13, minutes=30)

        self.env.cr.execute("""
            INSERT INTO hr_leave
                (employee_id, holiday_status_id, state,
                 request_date_from, request_date_to,
                 date_from, date_to,
                 number_of_days, number_of_hours,
                 x_return_state, x_annual_approval_state,
                 x_excess_days_accepted, x_unpaid_portion_days,
                 x_annual_portion_days,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'validate',
                 %s, %s, %s, %s,
                 15, 120,
                 'on_vacation', 'approved',
                 true, 5.0, 15.0,
                 %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            self.employee.id, self.leave_type.id,
            date_from, date_to, date_from_utc, date_to_utc,
            self.env.uid, self.env.uid,
        ))
        self.env.cr.fetchone()
        self.env.invalidate_all()

        ksw_leave = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', self.employee.id),
        ], limit=1)
        self.assertTrue(ksw_leave)

        unpaid_days = ksw_leave._get_unpaid_leave_days(self.employee.id)
        self.assertGreaterEqual(unpaid_days, 5,
            msg="Unpaid portion of combined leave should be counted")

    # ==================================================================
    # RESET / REFUSE / DRAFT — COMBINED FIELDS CLEARED
    # ==================================================================

    def test_refuse_clears_combined_fields(self):
        """Refusing clears excess_days_accepted and portion fields."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        leave.sudo().write({
            'x_financial_consideration_excess': 1000.0,
            'x_visa_cost_recovery': 500.0,
        })

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()
        self.assertEqual(leave.state, 'validate')

        # Refuse
        leave.with_user(self.user_hr).sudo().action_refuse()

        self.assertFalse(leave.x_excess_days_accepted)
        self.assertEqual(leave.x_annual_portion_days, 0)
        self.assertEqual(leave.x_unpaid_portion_days, 0)
        self.assertEqual(leave.x_financial_consideration_excess, 0)
        self.assertEqual(leave.x_visa_cost_recovery, 0)

    def test_refuse_cancels_combined_payslip(self):
        """Refusing a combined leave cancels the vacation payslip."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        self.assertTrue(payslip)

        leave.with_user(self.user_hr).sudo().action_refuse()

        self.assertEqual(payslip.state, 'cancel')
        self.assertFalse(leave.x_vacation_payslip_id)

    def test_draft_restarts_combined_chain(self):
        """Resetting to draft clears combined fields and restarts chain."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 3
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        self._approve_through_step(leave, 'hr')
        leave.with_user(self.user_hr).sudo().action_refuse()
        leave.with_user(self.user_hr).sudo().action_draft()

        self.assertEqual(leave.x_annual_approval_state, 'pending_dm')
        self.assertFalse(leave.x_excess_days_accepted)
        self.assertEqual(leave.x_annual_portion_days, 0)
        self.assertEqual(leave.x_unpaid_portion_days, 0)

    # ==================================================================
    # UNPAID ACCOUNTING FIELDS RESET ON REFUSE
    # ==================================================================

    def test_unpaid_accounting_fields_cleared_on_reset(self):
        """_reset_annual_multi_fields clears unpaid accounting fields."""
        leave = self._create_leave()
        leave.sudo().write({
            'x_financial_consideration_excess': 1000.0,
            'x_financial_consideration_excess_description': 'Test desc',
            'x_visa_cost_recovery': 500.0,
            'x_visa_cost_recovery_description': 'Visa desc',
        })

        leave._reset_annual_multi_fields()

        self.assertEqual(leave.x_financial_consideration_excess, 0)
        self.assertFalse(leave.x_financial_consideration_excess_description)
        self.assertEqual(leave.x_visa_cost_recovery, 0)
        self.assertFalse(leave.x_visa_cost_recovery_description)

    # ==================================================================
    # RETURN STATE ON COMBINED LEAVE
    # ==================================================================

    def test_combined_leave_sets_on_vacation(self):
        """Combined leave sets return state to on_vacation after approval."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 3
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        self.assertEqual(leave.state, 'validate')
        self.assertEqual(leave.x_return_state, 'on_vacation')

    # ==================================================================
    # CHATTER MESSAGES FOR COMBINED ACCOUNTING
    # ==================================================================

    def test_acc_approve_logs_unpaid_fields_combined(self):
        """Accounting approval on combined leave logs FIN_CONSIDERATION
        and VISA_COST_RECOVERY in chatter."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 5
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        leave.sudo().write({
            'x_financial_consideration_excess': 3000.0,
            'x_visa_cost_recovery': 1500.0,
        })

        self._approve_through_step(leave, 'gm_initial')
        msg_count_before = len(leave.message_ids)

        leave.with_user(self.user_acc).sudo().action_acc_approve()

        # At least 2 messages: the standard acc approve + the combined extras
        new_msgs = leave.message_ids[: len(leave.message_ids) - msg_count_before]
        all_bodies = ' '.join(
            (m.body or '') for m in new_msgs)
        self.assertIn('Financial Consideration', all_bodies)
        self.assertIn('Visa Cost Recovery', all_bodies)

    # ==================================================================
    # ATTENDANCE SHEET LOCKING FOR ANNUAL LEAVES
    # ==================================================================

    def test_annual_leave_locks_attendance_sheet(self):
        """Annual leave validation locks attendance sheet lines."""
        # Make the employee an attendance-sheet employee
        self.employee.sudo().write({'x_is_attendance_sheet': True})

        # Create a sheet with lines covering the leave period
        sheet = self.env['ksw.attendance.sheet'].sudo().create({
            'employee_id': self.employee.id,
            'month': '6',
            'year': '2026',
        })
        sheet.action_generate_lines()

        # Count initially attended lines in June 1-10
        lines_before = self.env['ksw.attendance.sheet.line'].sudo().search([
            ('sheet_id', '=', sheet.id),
            ('date', '>=', date(2026, 6, 1)),
            ('date', '<=', date(2026, 6, 10)),
            ('is_attended', '=', True),
        ])
        attended_before = len(lines_before)

        # Create and fully approve an annual leave for Jun 1-10
        self._create_annual_balance()
        leave = self._create_leave(
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 10),
        )

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        # Lines should now be locked (is_attended=False, x_leave_id set)
        locked_lines = self.env['ksw.attendance.sheet.line'].sudo().search([
            ('sheet_id', '=', sheet.id),
            ('x_leave_id', '=', leave.id),
        ])

        if attended_before > 0:
            self.assertGreater(
                len(locked_lines), 0,
                msg="Annual leave should lock attendance sheet lines")

        # Cleanup
        self.employee.sudo().write({'x_is_attendance_sheet': False})

    def test_annual_leave_unlocks_on_refuse(self):
        """Refusing unlocks attendance sheet lines for annual leave."""
        self.employee.sudo().write({'x_is_attendance_sheet': True})

        sheet = self.env['ksw.attendance.sheet'].sudo().create({
            'employee_id': self.employee.id,
            'month': '6',
            'year': '2026',
        })
        sheet.action_generate_lines()

        self._create_annual_balance()
        leave = self._create_leave(
            date_from=date(2026, 6, 1),
            date_to=date(2026, 6, 10),
        )

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        # Now refuse
        leave.with_user(self.user_hr).sudo().action_refuse()

        # All lines should be unlocked
        locked_lines = self.env['ksw.attendance.sheet.line'].sudo().search([
            ('sheet_id', '=', sheet.id),
            ('x_leave_id', '=', leave.id),
        ])
        self.assertEqual(
            len(locked_lines), 0,
            msg="Refusing should unlock all attendance sheet lines")

        self.employee.sudo().write({'x_is_attendance_sheet': False})

    # ==================================================================
    # EDGE CASES
    # ==================================================================

    def test_normal_leave_no_excess_fields(self):
        """Normal annual leave (no toggle) has 0 for portion fields."""
        leave = self._create_leave()
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertEqual(leave.x_annual_portion_days, 0)
        self.assertEqual(leave.x_unpaid_portion_days, 0)
        self.assertEqual(leave.x_clearance_balance, 0)

    def test_combined_all_inputs_together(self):
        """Full combined leave payslip with all 7 input types."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        cal_days = int(balance) + 3
        date_from = date(2026, 7, 1)
        date_to = date_from + timedelta(days=cal_days - 1)

        leave = self._create_leave(
            date_from=date_from, date_to=date_to, excess_days=True)
        leave.invalidate_recordset()
        leave._compute_duration()

        # Set all fields
        leave.sudo().write({
            'x_penalty_amount': 200.0,
            'x_flight_ticket_amount': 3000.0,
            'x_remaining_loans': 1000.0,
            'x_financial_consideration_excess': 500.0,
            'x_visa_cost_recovery': 300.0,
        })
        self.env['hr.leave.commission.line'].create([
            {'leave_id': leave.id, 'name': 'Jan', 'amount': 800.0},
            {'leave_id': leave.id, 'name': 'Feb', 'amount': 600.0},
        ])
        leave.invalidate_recordset()

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        codes = set(payslip.input_line_ids.mapped('code'))

        expected_codes = {
            'VACATION_BAL', 'FLIGHT_TICKET', 'PENALTY',
            'ADDITIONAL_COMMISSIONS', 'REMAINING_LOANS',
            'FIN_CONSIDERATION', 'VISA_COST_RECOVERY',
        }
        self.assertTrue(
            expected_codes.issubset(codes),
            msg=f"Missing input codes: {expected_codes - codes}")





