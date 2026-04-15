# -*- coding: utf-8 -*-
"""Tests for annual leave toggle state machine.

Covers edge cases around x_is_full_clearance and x_excess_days_accepted
toggles:
  - Unchecking excess accepted triggers allocation validation
  - Unchecking full clearance triggers allocation validation
  - Full clearance auto-clears when dates exceed balance
  - Excess accepted auto-clears when dates shrink below balance
  - Changing leave type to non-annual clears all toggles
  - Refuse / draft / back-to-approval clears all toggles
  - Consistency after multiple toggle state transitions
"""
from datetime import date, datetime, timedelta

from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestToggleState(TransactionCase):
    """Tests for the full-clearance / excess-days toggle state machine."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Work schedule ──
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'Test Toggle Group',
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
            'name': 'Test Toggle Calendar',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })

        # ── Users ──
        cls.user_dm = cls.env['res.users'].create({
            'name': 'DM Toggle',
            'login': 'test_dm_toggle',
            'email': 'dm_toggle@test.com',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.emp_dm = cls.env['hr.employee'].create({
            'name': 'DM Toggle Employee',
            'user_id': cls.user_dm.id,
        })

        cls.user_hr = cls.env['res.users'].create({
            'name': 'HR Toggle',
            'login': 'test_hr_toggle',
            'email': 'hr_toggle@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('hr_holidays.group_hr_holidays_user').id,
            ])],
        })
        cls.emp_hr = cls.env['hr.employee'].create({
            'name': 'HR Toggle Employee',
            'user_id': cls.user_hr.id,
        })

        cls.user_gm = cls.env['res.users'].create({
            'name': 'GM Toggle',
            'login': 'test_gm_toggle',
            'email': 'gm_toggle@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_gm').id,
            ])],
        })
        cls.emp_gm = cls.env['hr.employee'].create({
            'name': 'GM Toggle Employee',
            'user_id': cls.user_gm.id,
        })

        cls.user_acc = cls.env['res.users'].create({
            'name': 'ACC Toggle',
            'login': 'test_acc_toggle',
            'email': 'acc_toggle@test.com',
            'group_ids': [(6, 0, [
                cls.env.ref('base.group_user').id,
                cls.env.ref('KSW_annual_leave.group_annual_leave_acc').id,
            ])],
        })
        cls.emp_acc = cls.env['hr.employee'].create({
            'name': 'ACC Toggle Employee',
            'user_id': cls.user_acc.id,
        })

        # ── Employee requesting leave ──
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Test Toggle Employee',
            'resource_calendar_id': cls.calendar.id,
            'leave_manager_id': cls.user_dm.id,
        })

        # ── Version (contract) ──
        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'Test Version Toggle',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': cls.calendar.id,
            'wage': 6000.0,
            'hra': 1500.0,
            'struct_id': cls.env.ref('om_hr_payroll.structure_base').id,
        })
        cls.employee._compute_current_version_id()

        # ── Annual leave type with multi-step validation + requires_allocation ──
        cls.leave_type_with_alloc = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave Toggle Test (Alloc)',
            'requires_allocation': True,
            'leave_validation_type': 'annual_multi',
            'is_annual_leave': True,
        })

        # ── Annual leave type WITHOUT allocation ──
        cls.leave_type_no_alloc = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave Toggle Test (No Alloc)',
            'requires_allocation': False,
            'leave_validation_type': 'annual_multi',
            'is_annual_leave': True,
        })

        # ── Non-annual leave type ──
        cls.leave_type_normal = cls.env['hr.leave.type'].create({
            'name': 'Sick Leave Toggle Test',
            'requires_allocation': False,
            'is_annual_leave': False,
        })

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _create_leave_sql(self, date_from=None, date_to=None,
                          excess_days=False, full_clearance=False,
                          leave_type=None):
        """Create an annual_multi leave request via raw SQL to bypass
        _check_validity during creation."""
        date_from = date_from or date(2026, 8, 1)
        date_to = date_to or date(2026, 8, 10)
        lt = leave_type or self.leave_type_no_alloc
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
            self.employee.id, lt.id,
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

    def _create_allocation(self, days=15.0):
        """Create an explicit allocation for the requires_allocation type."""
        alloc = self.env['hr.leave.allocation'].sudo().create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type_with_alloc.id,
            'number_of_days': days,
        })
        alloc.action_approve()
        return alloc

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
    # BUG 1: Unchecking x_excess_days_accepted triggers allocation check
    # ==================================================================

    def test_uncheck_excess_triggers_allocation_validation(self):
        """Unchecking x_excess_days_accepted when days > allocation
        must raise ValidationError from _check_validity."""
        # Use a leave type that requires allocation
        # Create the ksw.annual.leave record which syncs an allocation
        ksw_rec = self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0, "Need positive balance for this test")

        # Create leave with more days than balance
        exceed_days = int(balance) + 10
        date_from = date(2026, 8, 1)
        date_to = date_from + timedelta(days=exceed_days - 1)

        # Use the leave_type_with_alloc — need an allocation for it
        alloc = self._create_allocation(days=balance)

        leave = self._create_leave_sql(
            date_from=date_from,
            date_to=date_to,
            excess_days=True,
            leave_type=self.leave_type_with_alloc,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # With excess accepted, number_of_days should = balance
        self.assertAlmostEqual(leave.number_of_days, balance, places=2,
            msg="With excess accepted, number_of_days should equal balance")

        # Now uncheck excess — should trigger _check_validity via write()
        with self.assertRaises(ValidationError):
            leave.write({'x_excess_days_accepted': False})

    def test_uncheck_full_clearance_triggers_allocation_validation(self):
        """Unchecking x_is_full_clearance when cal_days <= allocation
        should NOT raise (days fit within allocation)."""
        ksw_rec = self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0)

        alloc = self._create_allocation(days=balance)

        # Create a leave with few days + full clearance
        short_days = max(int(balance) - 5, 1)
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=short_days - 1),
            full_clearance=True,
            leave_type=self.leave_type_with_alloc,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # short_days <= allocation, so unchecking should NOT raise
        leave.write({'x_is_full_clearance': False})
        self.assertEqual(leave.x_is_full_clearance, False)
        self.assertAlmostEqual(leave.number_of_days, short_days, places=0)

    # ==================================================================
    # BUG 2: Full clearance auto-clears when dates exceed balance
    # ==================================================================

    def test_full_clearance_auto_clears_when_exceeds_balance(self):
        """When x_is_full_clearance is True and dates are changed to exceed
        balance, _compute_duration should auto-clear x_is_full_clearance
        and set x_exceeds_annual_balance = True."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0)

        # Start with dates within balance + full clearance
        short_days = max(int(balance) - 3, 1)
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=short_days - 1),
            full_clearance=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # Full clearance should be active (days <= balance)
        self.assertTrue(leave.x_is_full_clearance)
        self.assertFalse(leave.x_exceeds_annual_balance)

        # Now simulate changing dates to exceed balance
        exceed_days = int(balance) + 10
        new_date_to = date(2026, 8, 1) + timedelta(days=exceed_days - 1)
        new_date_to_utc = datetime.combine(
            new_date_to, datetime.min.time()) + timedelta(hours=13, minutes=30)

        leave.sudo().write({
            'request_date_to': new_date_to,
            'date_to': new_date_to_utc,
        })
        leave.invalidate_recordset()
        leave._compute_duration()

        # Full clearance should be auto-cleared
        self.assertFalse(
            leave.x_is_full_clearance,
            msg="Full clearance must auto-clear when days exceed balance")
        self.assertTrue(
            leave.x_exceeds_annual_balance,
            msg="x_exceeds_annual_balance should be True")
        # number_of_days should be cal_days (not capped to balance)
        self.assertAlmostEqual(
            leave.number_of_days, exceed_days, places=0,
            msg="number_of_days should be full calendar days after "
                "full clearance is cleared")

    def test_full_clearance_stays_when_under_balance(self):
        """Full clearance should NOT be auto-cleared when days <= balance."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0)

        short_days = max(int(balance) - 5, 1)
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=short_days - 1),
            full_clearance=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertTrue(leave.x_is_full_clearance)
        self.assertFalse(leave.x_exceeds_annual_balance)
        # number_of_days should be balance, not cal_days
        self.assertAlmostEqual(
            leave.number_of_days, balance, places=2)

    # ==================================================================
    # Auto-clear excess when days shrink below balance
    # ==================================================================

    def test_excess_auto_clears_when_days_under_balance(self):
        """x_excess_days_accepted should auto-clear when dates are changed
        so that days no longer exceed balance."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0)

        # Start with excess days
        exceed_days = int(balance) + 5
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=exceed_days - 1),
            excess_days=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertTrue(leave.x_excess_days_accepted)

        # Shrink dates to below balance
        short_days = max(int(balance) - 3, 1)
        new_date_to = date(2026, 8, 1) + timedelta(days=short_days - 1)
        new_date_to_utc = datetime.combine(
            new_date_to, datetime.min.time()) + timedelta(hours=13, minutes=30)
        leave.sudo().write({
            'request_date_to': new_date_to,
            'date_to': new_date_to_utc,
        })
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertFalse(
            leave.x_excess_days_accepted,
            msg="Excess accepted should auto-clear when days ≤ balance")
        self.assertFalse(leave.x_exceeds_annual_balance)

    # ==================================================================
    # Changing leave type to non-annual clears toggles
    # ==================================================================

    def test_change_to_non_annual_clears_toggles(self):
        """Changing holiday_status_id to a non-annual type should clear
        both x_is_full_clearance and x_excess_days_accepted."""
        self._create_annual_balance()
        balance = self._get_actual_balance()

        # Create with full clearance
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            full_clearance=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertTrue(leave.x_is_full_clearance)

        # Change to non-annual type
        leave.sudo().write({
            'holiday_status_id': self.leave_type_normal.id,
        })
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertFalse(
            leave.x_is_full_clearance,
            msg="Full clearance should be cleared for non-annual leave type")
        self.assertFalse(leave.x_exceeds_annual_balance)

    def test_change_to_non_annual_clears_excess(self):
        """Changing leave type to non-annual clears excess toggle."""
        self._create_annual_balance()
        balance = self._get_actual_balance()

        exceed_days = int(balance) + 5
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=exceed_days - 1),
            excess_days=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertTrue(leave.x_excess_days_accepted)

        leave.sudo().write({
            'holiday_status_id': self.leave_type_normal.id,
        })
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertFalse(leave.x_excess_days_accepted)

    # ==================================================================
    # Refuse / draft resets toggle fields
    # ==================================================================

    def test_refuse_clears_full_clearance(self):
        """Refusing a leave with full clearance should clear the toggle."""
        self._create_annual_balance()

        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            full_clearance=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertTrue(leave.x_is_full_clearance)

        # Approve through all steps
        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()
        self.assertEqual(leave.state, 'validate')

        # Refuse
        leave.with_user(self.user_hr).sudo().action_refuse()

        self.assertFalse(
            leave.x_is_full_clearance,
            msg="Full clearance should be cleared on refuse")
        self.assertFalse(leave.x_excess_days_accepted)

    def test_draft_clears_full_clearance(self):
        """Resetting to draft should clear full clearance."""
        self._create_annual_balance()

        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            full_clearance=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # Advance to HR step then refuse + reset to draft
        self._approve_through_step(leave, 'hr')
        leave.with_user(self.user_hr).sudo().action_refuse()
        leave.with_user(self.user_hr).sudo().action_draft()

        self.assertFalse(leave.x_is_full_clearance)
        self.assertEqual(leave.x_annual_approval_state, 'pending_dm')

    def test_back_to_approval_clears_toggles(self):
        """_move_validate_leave_to_confirm clears full clearance."""
        self._create_annual_balance()

        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            full_clearance=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # Fully approve
        self._approve_through_step(leave, 'acc')
        leave.with_user(self.user_gm).sudo().action_gm_final_approve()
        self.assertEqual(leave.state, 'validate')

        # Back to approval
        leave.with_user(self.user_hr).sudo()._move_validate_leave_to_confirm()

        self.assertFalse(leave.x_is_full_clearance)
        self.assertEqual(leave.x_annual_approval_state, 'pending_dm')

    # ==================================================================
    # Mutual exclusivity: full clearance ↔ excess accepted
    # ==================================================================

    def test_mutual_exclusivity_full_clearance_and_excess(self):
        """Full clearance and excess accepted cannot both be True after
        _compute_duration because full clearance is hidden when exceeds."""
        self._create_annual_balance()
        balance = self._get_actual_balance()

        # Create with BOTH flags set and days > balance
        exceed_days = int(balance) + 5
        date_from = date(2026, 8, 1)
        date_to = date_from + timedelta(days=exceed_days - 1)

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
                 x_excess_days_accepted, x_is_full_clearance,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'confirm',
                 %s, %s, %s, %s,
                 %s, %s,
                 'not_applicable', 'pending_dm',
                 true, true,
                 %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            self.employee.id, self.leave_type_no_alloc.id,
            date_from, date_to, date_from_utc, date_to_utc,
            exceed_days, exceed_days * 8.0,
            self.env.uid, self.env.uid,
        ))
        leave_id = self.env.cr.fetchone()[0]
        self.env.invalidate_all()
        leave = self.env['hr.leave'].browse(leave_id)

        leave.invalidate_recordset()
        leave._compute_duration()

        # Full clearance should be cleared because days > balance
        self.assertFalse(
            leave.x_is_full_clearance,
            msg="Full clearance should be auto-cleared when days > balance")
        # Excess should still be True
        self.assertTrue(leave.x_excess_days_accepted)

    def test_no_double_flag_when_under_balance(self):
        """When days ≤ balance and both flags set, full clearance wins
        and excess is auto-cleared (exceeds is False)."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        short_days = max(int(balance) - 3, 1)

        date_from = date(2026, 8, 1)
        date_to = date_from + timedelta(days=short_days - 1)
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
                 x_excess_days_accepted, x_is_full_clearance,
                 create_uid, write_uid, create_date, write_date)
            VALUES
                (%s, %s, 'confirm',
                 %s, %s, %s, %s,
                 %s, %s,
                 'not_applicable', 'pending_dm',
                 true, true,
                 %s, %s, NOW(), NOW())
            RETURNING id
        """, (
            self.employee.id, self.leave_type_no_alloc.id,
            date_from, date_to, date_from_utc, date_to_utc,
            short_days, short_days * 8.0,
            self.env.uid, self.env.uid,
        ))
        leave_id = self.env.cr.fetchone()[0]
        self.env.invalidate_all()
        leave = self.env['hr.leave'].browse(leave_id)

        leave.invalidate_recordset()
        leave._compute_duration()

        # Full clearance should stay (days ≤ balance)
        self.assertTrue(leave.x_is_full_clearance)
        # Excess should be auto-cleared (not exceeds)
        self.assertFalse(leave.x_excess_days_accepted)

    # ==================================================================
    # Compute duration consistency after rapid toggle changes
    # ==================================================================

    def test_toggle_on_off_full_clearance_consistency(self):
        """Toggling full clearance on/off should leave state consistent."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        short_days = max(int(balance) - 3, 1)

        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=short_days - 1),
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # Initially: no flags
        self.assertFalse(leave.x_is_full_clearance)
        self.assertAlmostEqual(leave.number_of_days, short_days, places=0)

        # Toggle ON
        leave.sudo().write({'x_is_full_clearance': True})
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertTrue(leave.x_is_full_clearance)
        self.assertAlmostEqual(leave.number_of_days, balance, places=2)

        # Toggle OFF
        leave.sudo().write({'x_is_full_clearance': False})
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertFalse(leave.x_is_full_clearance)
        self.assertAlmostEqual(leave.number_of_days, short_days, places=0)

    def test_toggle_on_off_excess_consistency(self):
        """Toggling excess on/off should leave state consistent."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        exceed_days = int(balance) + 5

        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=exceed_days - 1),
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # Initially: no excess flag, number_of_days = cal_days
        self.assertFalse(leave.x_excess_days_accepted)
        self.assertAlmostEqual(leave.number_of_days, exceed_days, places=0)
        self.assertTrue(leave.x_exceeds_annual_balance)

        # Toggle ON excess
        leave.sudo().write({'x_excess_days_accepted': True})
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertTrue(leave.x_excess_days_accepted)
        self.assertAlmostEqual(leave.number_of_days, balance, places=2)

        # Toggle OFF excess
        leave.sudo().write({'x_excess_days_accepted': False})
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertFalse(leave.x_excess_days_accepted)
        self.assertAlmostEqual(leave.number_of_days, exceed_days, places=0)

    # ==================================================================
    # x_exceeds_annual_balance tracking
    # ==================================================================

    def test_exceeds_balance_flag_set_correctly(self):
        """x_exceeds_annual_balance should be True when cal_days > balance."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        self.assertGreater(balance, 0)

        # Under balance
        short_days = max(int(balance) - 3, 1)
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=short_days - 1),
        )
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertFalse(leave.x_exceeds_annual_balance)

    def test_exceeds_balance_flag_true_when_over(self):
        """x_exceeds_annual_balance should be True when cal_days > balance."""
        self._create_annual_balance()
        balance = self._get_actual_balance()
        exceed_days = int(balance) + 5

        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 1) + timedelta(days=exceed_days - 1),
        )
        leave.invalidate_recordset()
        leave._compute_duration()
        self.assertTrue(leave.x_exceeds_annual_balance)

    # ==================================================================
    # Non-annual leave should have all toggle fields as False/0
    # ==================================================================

    def test_non_annual_leave_zeros(self):
        """Non-annual leave should have all toggle fields as False/0."""
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
            leave_type=self.leave_type_normal,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        self.assertFalse(leave.x_is_full_clearance)
        self.assertFalse(leave.x_excess_days_accepted)
        self.assertFalse(leave.x_exceeds_annual_balance)
        self.assertEqual(leave.x_clearance_balance, 0)
        self.assertEqual(leave.x_annual_portion_days, 0)
        self.assertEqual(leave.x_unpaid_portion_days, 0)

    # ==================================================================
    # Write override does NOT trigger _check_validity for non-toggle fields
    # ==================================================================

    def test_write_non_toggle_fields_no_validity_check(self):
        """Writing non-toggle fields should NOT trigger extra _check_validity."""
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 5),
        )
        # Should not raise
        leave.sudo().write({'x_penalty_amount': 100.0})

    # ==================================================================
    # Full clearance on a leave without balance -> cal_days used
    # ==================================================================

    def test_full_clearance_no_balance_uses_cal_days(self):
        """When full clearance is checked but no ksw.annual.leave record
        exists (balance = 0), number_of_days should use cal_days."""
        # Don't create annual balance - balance will be 0
        leave = self._create_leave_sql(
            date_from=date(2026, 8, 1),
            date_to=date(2026, 8, 10),
            full_clearance=True,
        )
        leave.invalidate_recordset()
        leave._compute_duration()

        # balance = 0, so "exceeds" is False (need both cal_days > 0
        # AND balance > 0 for exceeds to be True)
        self.assertFalse(leave.x_exceeds_annual_balance)
        # With full clearance, balance = 0 → falls to else branch
        # (balance > 0 is False), so uses cal_days
        self.assertAlmostEqual(leave.number_of_days, 10.0, places=0)




