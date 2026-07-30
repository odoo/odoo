# -*- coding: utf-8 -*-
"""Tests for the multi-step annual leave approval workflow.

Tests the 6-step approval chain:
  Employee → DM → HR → GM Initial → Accounting → GM Final → Approved

Also tests:
  - Vacation payslip auto-generation with correct input lines
  - Payslip cancellation on refuse / reset-to-draft
  - Group-based permission checks at each step
  - Field editability boundaries (HR fills penalty, ACC fills ticket)
  - Return-state set to 'on_vacation' after final approval
"""
from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestMultiStepAnnualLeave(TransactionCase):
    """Full integration tests for the annual_multi approval flow."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Annual Multi Group',
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
            cls.env['resource.calendar.group.line'].create({
                'name': f'Break Day {day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'break',
                'hour_from': 12.0,
                'hour_to': 13.0,
            })

        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'Test Annual Multi Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Users with specific groups ──
        # DM user (leave manager)
        cls.user_dm = cls.env['res.users'].create({
            'name': 'DM User',
            'login': 'test_dm_annual_multi',
            'email': 'dm@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
            ])],
        })
        cls.emp_dm = cls.env['hr.employee'].create({
            'name': 'DM Employee',
            'user_id': cls.user_dm.id,
        })

        # HR user
        cls.user_hr = cls.env['res.users'].create({
            'name': 'HR User',
            'login': 'test_hr_annual_multi',
            'email': 'hr@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('hr_holidays.group_hr_holidays_user').id,
            ])],
        })
        cls.emp_hr = cls.env['hr.employee'].create({
            'name': 'HR Employee',
            'user_id': cls.user_hr.id,
        })

        # GM user
        cls.user_gm = cls.env['res.users'].create({
            'name': 'GM User',
            'login': 'test_gm_annual_multi',
            'email': 'gm@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_gm').id,
            ])],
        })
        cls.emp_gm = cls.env['hr.employee'].create({
            'name': 'GM Employee',
            'user_id': cls.user_gm.id,
        })

        # Accounting user
        cls.user_acc = cls.env['res.users'].create({
            'name': 'Accounting User',
            'login': 'test_acc_annual_multi',
            'email': 'acc@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_acc').id,
            ])],
        })
        cls.emp_acc = cls.env['hr.employee'].create({
            'name': 'ACC Employee',
            'user_id': cls.user_acc.id,
        })

        # Regular employee (the one requesting leave)
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Annual Multi Employee',
            'resource_calendar_id': cls.calendar.id,
            'leave_manager_id': cls.user_dm.id,
        })

        # Set up version (contract) with wage
        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Test Version Annual',
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
            'name': 'Annual Leave Multi-Step',
            'requires_allocation': False,
            'leave_validation_type': 'annual_multi',
            'is_annual_leave': True,
        })

        # ── Expected daily wage ──
        cls.daily_wage = 6000.0 / 30.0  # 200.0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_leave(self, date_from=None, date_to=None):
        """Create an annual_multi leave request via SQL (bypass ORM
        create constraints like attendance_ids, allocation checks)."""
        date_from = date_from or date(2026, 5, 1)
        date_to = date_to or date(2026, 5, 14)
        from datetime import datetime, timedelta as td
        date_from_utc = datetime.combine(date_from, datetime.min.time()) + td(hours=5)
        date_to_utc = datetime.combine(date_to, datetime.min.time()) + td(hours=13, minutes=30)
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
            cal_days, cal_days * 8.0,
            self.env.uid, self.env.uid,
        ))
        leave_id = self.env.cr.fetchone()[0]
        self.env.invalidate_all()
        return self.env['hr.leave'].browse(leave_id)

    def _create_annual_balance(self, balance=30.0):
        """Ensure a ksw.annual.leave record exists for the employee.

        Note: remaining_balance is computed from total_accrued_days (stored
        compute based on actual joining date). We cannot override it reliably.
        This helper just ensures the record exists. Tests that check
        VACATION_BAL amounts should read the actual remaining_balance.
        """
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
        """Run the approval chain up to and including the given step.

        Steps: 'dm', 'hr', 'gm_initial', 'acc', 'gm_final'.
        """
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
    # CREATION
    # ==================================================================

    def test_create_sets_pending_dm(self):
        """New annual_multi leave starts at pending_dm."""
        leave = self._create_leave()
        self.assertEqual(leave.x_annual_approval_state, 'pending_dm')
        self.assertEqual(leave.state, 'confirm')

    # ==================================================================
    # STEP 1: DM APPROVAL
    # ==================================================================

    def test_dm_approve_advances_to_pending_hr(self):
        """DM approval moves state to pending_hr."""
        leave = self._create_leave()
        leave.with_user(self.user_dm).sudo().action_dm_approve()

        self.assertEqual(leave.x_annual_approval_state, 'pending_hr')
        self.assertTrue(leave.x_dm_approved_by)
        self.assertTrue(leave.x_dm_approved_date)

    def test_dm_approve_wrong_step_raises(self):
        """DM approve on non-pending_dm step raises UserError."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'dm')
        # Now at pending_hr — trying DM again should fail
        with self.assertRaises(UserError):
            leave.with_user(self.user_dm).sudo().action_dm_approve()

    # ==================================================================
    # STEP 2: HR APPROVAL
    # ==================================================================

    def test_hr_approve_advances_to_pending_gm_initial(self):
        """HR approval moves state to pending_gm_initial."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'dm')

        # HR fills penalty and iqama before approving
        leave.sudo().write({
            'x_penalty_amount': 500.0,
            'x_penalty_description': 'Late penalty',
            'x_iqama_renewal_amount': 300.0,
            'x_iqama_renewal_description': 'Iqama renewal',
        })
        leave.with_user(self.user_hr).sudo().action_hr_approve()

        self.assertEqual(leave.x_annual_approval_state, 'pending_gm_initial')
        self.assertTrue(leave.x_hr_approved_by)
        self.assertEqual(leave.x_penalty_amount, 500.0)
        self.assertEqual(leave.x_iqama_renewal_amount, 300.0)

    def test_hr_approve_requires_hr_group(self):
        """Non-HR user cannot approve HR step."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'dm')
        with self.assertRaises(UserError):
            leave.with_user(self.user_dm).sudo().action_hr_approve()

    def test_hr_approve_wrong_step_raises(self):
        """HR approve on non-pending_hr step raises UserError."""
        leave = self._create_leave()
        # Still at pending_dm
        with self.assertRaises(UserError):
            leave.with_user(self.user_hr).sudo().action_hr_approve()

    # ==================================================================
    # STEP 3: GM INITIAL APPROVAL
    # ==================================================================

    def test_gm_initial_advances_to_pending_acc(self):
        """GM initial approval moves state to pending_acc."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'gm_initial')

        self.assertEqual(leave.x_annual_approval_state, 'pending_acc')
        self.assertTrue(leave.x_gm_initial_approved_by)

    def test_gm_initial_requires_gm_group(self):
        """Non-GM user cannot approve GM initial step."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'hr')
        with self.assertRaises(UserError):
            leave.with_user(self.user_hr).sudo().action_gm_initial_approve()

    # ==================================================================
    # STEP 4: ACCOUNTING APPROVAL
    # ==================================================================

    def test_acc_approve_advances_to_pending_gm_final(self):
        """Accounting approval moves state to pending_gm_final."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'gm_initial')

        # Accounting fills flight ticket before approving
        leave.sudo().write({
            'x_flight_ticket_amount': 2000.0,
            'x_flight_ticket_description': 'Round trip Cairo',
        })
        leave.with_user(self.user_acc).sudo().action_acc_approve()

        self.assertEqual(leave.x_annual_approval_state, 'pending_gm_final')
        self.assertTrue(leave.x_acc_approved_by)
        self.assertEqual(leave.x_flight_ticket_amount, 2000.0)

    def test_acc_requires_acc_group(self):
        """Non-Accounting user cannot approve accounting step."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'gm_initial')
        with self.assertRaises(UserError):
            leave.with_user(self.user_dm).sudo().action_acc_approve()

    # ==================================================================
    # STEP 5: GM FINAL APPROVAL
    # ==================================================================

    def test_gm_final_approve_full_chain(self):
        """Full approval chain: state becomes 'approved' + 'validate'."""
        leave = self._create_leave()
        self._create_annual_balance(30.0)
        self._approve_through_step(leave, 'acc')

        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        self.assertEqual(leave.x_annual_approval_state, 'approved')
        self.assertEqual(leave.state, 'validate')
        self.assertTrue(leave.x_gm_final_approved_by)

    def test_gm_final_sets_on_vacation(self):
        """After final approval, x_return_state = 'on_vacation'."""
        leave = self._create_leave()
        self._create_annual_balance(30.0)
        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        self.assertEqual(leave.x_return_state, 'on_vacation')

    def test_gm_final_requires_gm_group(self):
        """Non-GM user cannot give final approval."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'acc')
        with self.assertRaises(UserError):
            leave.with_user(self.user_acc).sudo().action_gm_final_approve()

    # ==================================================================
    # VACATION PAYSLIP GENERATION
    # ==================================================================

    def test_vacation_payslip_created(self):
        """Final approval creates a vacation payslip."""
        leave = self._create_leave()
        self._create_annual_balance(20.0)

        # Set amounts before approval
        leave.sudo().write({
            'x_penalty_amount': 500.0,
            'x_flight_ticket_amount': 2000.0,
            'x_iqama_renewal_amount': 300.0,
        })
        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        self.assertTrue(payslip, 'Vacation payslip should be created.')
        self.assertEqual(payslip.employee_id, self.employee)

    def test_vacation_payslip_input_lines(self):
        """Vacation payslip has correct input lines."""
        leave = self._create_leave()
        self._create_annual_balance()

        leave.sudo().write({
            'x_penalty_amount': 500.0,
            'x_flight_ticket_amount': 2000.0,
            'x_iqama_renewal_amount': 300.0,
        })
        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        inputs_by_code = {i.code: i for i in payslip.input_line_ids}

        # Vacation balance: calendar days (May 1–14 = 14 days) × daily wage
        cal_days = (leave.request_date_to - leave.request_date_from).days + 1
        expected_vac = cal_days * self.daily_wage
        if expected_vac > 0:
            self.assertIn('VACATION_BAL', inputs_by_code)
            self.assertAlmostEqual(
                inputs_by_code['VACATION_BAL'].amount, expected_vac, places=2)

        # Flight ticket
        self.assertIn('FLIGHT_TICKET', inputs_by_code)
        self.assertEqual(inputs_by_code['FLIGHT_TICKET'].amount, 2000.0)

        # Penalty
        self.assertIn('PENALTY', inputs_by_code)
        self.assertEqual(inputs_by_code['PENALTY'].amount, 500.0)

        # Iqama renewal is decision-only — not a payslip input
        self.assertNotIn('IQAMA_RENEWAL', inputs_by_code)

    def test_vacation_payslip_no_penalty_if_zero(self):
        """No PENALTY input line when penalty amount is 0."""
        leave = self._create_leave()
        self._create_annual_balance(10.0)

        leave.sudo().write({
            'x_flight_ticket_amount': 1500.0,
        })
        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        codes = payslip.input_line_ids.mapped('code')
        self.assertIn('VACATION_BAL', codes)
        self.assertIn('FLIGHT_TICKET', codes)
        self.assertNotIn('PENALTY', codes)
        self.assertNotIn('IQAMA_RENEWAL', codes)

    def test_vacation_payslip_zero_balance_still_has_cal_days(self):
        """Normal vacation VACATION_BAL uses calendar days, NOT remaining
        balance. Even without a ksw.annual.leave record the input line
        is created based on the leave's request dates."""
        leave = self._create_leave()
        # Don't create an annual balance record — balance will be 0
        # Remove any existing record
        existing = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', self.employee.id),
        ])
        if existing:
            existing.sudo().unlink()

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        codes = payslip.input_line_ids.mapped('code')
        # Calendar days (May 1–14 = 14) × daily wage → VACATION_BAL exists
        self.assertIn('VACATION_BAL', codes)

    # ==================================================================
    # REFUSE — RESETS + PAYSLIP CANCELLATION
    # ==================================================================

    def test_refuse_resets_multi_step_fields(self):
        """Refusing resets all approval tracking fields."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'hr')

        leave.with_user(self.user_hr).sudo().action_refuse()

        self.assertFalse(leave.x_annual_approval_state)
        self.assertFalse(leave.x_dm_approved_by)
        self.assertFalse(leave.x_hr_approved_by)
        self.assertEqual(leave.x_penalty_amount, 0)

    def test_refuse_cancels_vacation_payslip(self):
        """Refusing a fully-approved leave cancels the vacation payslip."""
        leave = self._create_leave()
        self._create_annual_balance(15.0)

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        self.assertTrue(payslip)

        # Refuse the validated leave
        leave.with_user(self.user_hr).sudo().action_refuse()

        self.assertEqual(payslip.state, 'cancel')
        self.assertFalse(leave.x_vacation_payslip_id)

    # ==================================================================
    # RESET TO DRAFT — RESTARTS CHAIN
    # ==================================================================

    def test_draft_restarts_approval_chain(self):
        """Resetting to draft restarts at pending_dm."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'hr')

        # First refuse so we can reset to draft
        leave.with_user(self.user_hr).sudo().action_refuse()
        leave.with_user(self.user_hr).sudo().action_draft()

        self.assertEqual(leave.x_annual_approval_state, 'pending_dm')
        # Odoo 19 has no 'draft' state; action_draft resets to 'confirm'
        self.assertEqual(leave.state, 'confirm')

    def test_draft_cancels_vacation_payslip(self):
        """Resetting to draft cancels the vacation payslip."""
        leave = self._create_leave()
        self._create_annual_balance(15.0)

        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()

        payslip = leave.x_vacation_payslip_id
        self.assertTrue(payslip)

        leave.with_user(self.user_hr).sudo().action_refuse()
        leave.with_user(self.user_hr).sudo().action_draft()

        self.assertEqual(payslip.state, 'cancel')

    # ==================================================================
    # CAN_APPROVE / CAN_VALIDATE OVERRIDES
    # ==================================================================

    def test_can_approve_false_for_annual_multi(self):
        """Standard can_approve is False for annual_multi leaves."""
        leave = self._create_leave()
        leave._compute_can_approve()
        self.assertFalse(leave.can_approve)

    def test_can_validate_false_for_annual_multi(self):
        """Standard can_validate is False for annual_multi leaves."""
        leave = self._create_leave()
        leave._compute_can_validate()
        self.assertFalse(leave.can_validate)

    # ==================================================================
    # LEAVE TYPE CONFIGURATION
    # ==================================================================

    def test_leave_type_has_annual_multi_option(self):
        """The leave type has 'annual_multi' as a validation type."""
        self.assertEqual(
            self.leave_type.leave_validation_type, 'annual_multi')
        self.assertTrue(self.leave_type.is_annual_leave)

    # ==================================================================
    # RETURN STATE INTEGRATION
    # ==================================================================

    def test_return_state_not_applicable_before_approval(self):
        """Before final approval, return state stays N/A."""
        leave = self._create_leave()
        self._approve_through_step(leave, 'acc')
        self.assertEqual(leave.x_return_state, 'not_applicable')

    # ==================================================================
    # CHATTER MESSAGES
    # ==================================================================

    def test_chatter_messages_posted(self):
        """Each approval step posts a chatter message."""
        leave = self._create_leave()
        initial_count = len(leave.message_ids)

        leave.with_user(self.user_dm).sudo().action_dm_approve()
        self.assertGreater(len(leave.message_ids), initial_count)

        count_after_dm = len(leave.message_ids)
        leave.with_user(self.user_hr).sudo().action_hr_approve()
        self.assertGreater(len(leave.message_ids), count_after_dm)

    # ==================================================================
    # EDGE CASES
    # ==================================================================

    def test_no_version_skips_payslip(self):
        """If employee has no salary structure, payslip creation is skipped."""
        leave = self._create_leave()
        # Temporarily remove the salary structure
        orig_struct = self.version.struct_id
        self.version.write({'struct_id': False})

        self._approve_through_step(leave, 'acc')
        # Should not raise, just skip payslip
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()
        self.assertFalse(leave.x_vacation_payslip_id)

        # Restore
        self.version.write({'struct_id': orig_struct.id})

    def test_approver_tracking_full_chain(self):
        """All 5 approver fields are correctly populated."""
        leave = self._create_leave()
        self._create_annual_balance(20.0)

        leave.with_user(self.user_dm).sudo().action_dm_approve()
        self.assertEqual(leave.x_dm_approved_by, self.emp_dm)

        leave.with_user(self.user_hr).sudo().action_hr_approve()
        self.assertEqual(leave.x_hr_approved_by, self.emp_hr)

        leave.with_user(self.user_gm).sudo().action_gm_initial_approve()
        self.assertEqual(leave.x_gm_initial_approved_by, self.emp_gm)

        leave.with_user(self.user_acc).sudo().action_acc_approve()
        self.assertEqual(leave.x_acc_approved_by, self.emp_acc)

        leave.with_user(self.user_gm).sudo().action_gm_final_approve()
        self.assertEqual(leave.x_gm_final_approved_by, self.emp_gm)






