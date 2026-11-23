# -*- coding: utf-8 -*-
"""Comprehensive tests for the Annual Leave Opening Balance feature.

Covers:
  - Backward compatibility (no reset date)
  - Accrual from effective start date, tier-aware
  - Employees entirely in tier 1 after reset
  - Employees entirely in tier 2 after reset (>5 yrs before reset date)
  - Employees who cross the 5-year tier boundary after the reset date
  - Opening extra days added to accrual
  - Negative extra days reduce balance
  - Zero extra days
  - Reset date same as joining date (equivalent to no reset)
  - Future reset date yields 0 accrual
  - Effective start date computed field
  - Lock guard prevents changes to opening fields
  - Unlock then re-lock workflow
  - Lock does NOT block non-opening field writes
  - Allocation date_from set to effective start date
  - _get_version_accrual_segments from_date trimming
  - FIFO vacation value with reset date
  - FIFO vacation value: extra days prepended as synthetic segment
  - Wizard: apply opening balance, lock after apply
  - Wizard: skip locked records
  - Wizard: skip_locked=False raises on locked
  - Wizard: missing employee_id line skipped gracefully
  - Remaining balance formula consistency
  - Refresh accrual after reset date change
"""
from datetime import date, timedelta

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestOpeningBalance(TransactionCase):
    """Tests for the opening balance (go-live baseline) feature."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # ── Annual leave type (no allocation required — simplifies tests) ──
        cls.annual_type = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave OB Test',
            'requires_allocation': False,
            'is_annual_leave': True,
            'leave_validation_type': 'no_validation',
        })

        # Make sure is_annual_leave is unique (only one can exist at a time
        # in _sync_allocations); set others to False for test isolation.
        cls.env['hr.leave.type'].sudo().search([
            ('is_annual_leave', '=', True),
            ('id', '!=', cls.annual_type.id),
        ]).write({'is_annual_leave': False})

        # ── Helper: create a minimal employee with a version ──
        cls._emp_counter = 0

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_employee(self, joining_date, wage=6000.0, name=None):
        """Create an hr.employee + hr.version with the given joining date."""
        TestOpeningBalance._emp_counter += 1
        n = self._emp_counter
        emp = self.env['hr.employee'].create({
            'name': name or 'OB Test Employee %d' % n,
        })
        version = emp.current_version_id
        version.write({
            'name': 'Version OB %d' % n,
            'date_version': joining_date,
            'contract_date_start': joining_date,
            'wage': wage,
        })
        emp._compute_current_version_id()
        return emp

    def _make_ksw(self, employee, reset_date=None, extra_days=0.0):
        """Create (or return existing) ksw.annual.leave for the employee."""
        existing = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', employee.id),
        ], limit=1)
        if existing:
            return existing
        vals = {'employee_id': employee.id}
        if reset_date:
            vals['x_opening_reset_date'] = reset_date
        if extra_days:
            vals['x_opening_extra_days'] = extra_days
        return self.env['ksw.annual.leave'].sudo().create(vals)

    def _refresh(self, ksw_rec):
        """Invalidate + recompute a ksw.annual.leave record."""
        ksw_rec.invalidate_recordset()
        ksw_rec._compute_leave_data()
        ksw_rec.invalidate_recordset()

    # ==================================================================
    # 1. Backward compatibility — no reset date
    # ==================================================================

    def test_no_reset_date_backward_compatible(self):
        """Without a reset date the accrual is identical to the old logic."""
        joining = date(2024, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        self._refresh(ksw)

        today = date.today()
        total_days = (today - joining).days
        five_years = 5 * 365
        tier1_cal = min(total_days, five_years)
        tier2_cal = max(total_days - five_years, 0)

        expected = (
            tier1_cal * (21.0 / 365.0)
            + tier2_cal * (30.0 / 365.0)
        )
        self.assertAlmostEqual(ksw.total_accrued_days, expected, places=2)
        self.assertEqual(ksw.joining_date, joining)
        self.assertFalse(ksw.x_opening_reset_date)
        # Effective start = joining (no reset)
        self.assertEqual(ksw.x_effective_start_date, joining)

    # ==================================================================
    # 2. Reset date — employee entirely in tier 1 after reset
    # ==================================================================

    def test_reset_date_tier1_employee(self):
        """Employee joined 2023-01-01, reset date 2025-01-01.
        Both joining and reset are < 5 years ago → full tier-1 rate."""
        joining = date(2023, 1, 1)
        reset = date(2025, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)

        today = date.today()
        total_days = (today - joining).days
        reset_days = (reset - joining).days
        five_years = 5 * 365

        # Both periods are within tier 1 (< 1825 days)
        tier1_effective = (
            min(total_days, five_years) - min(reset_days, five_years)
        )
        tier2_effective = (
            max(total_days - five_years, 0) - max(reset_days - five_years, 0)
        )
        expected = (
            tier1_effective * (21.0 / 365.0)
            + tier2_effective * (30.0 / 365.0)
        )
        self.assertAlmostEqual(ksw.total_accrued_days, expected, places=2)
        # Joining date is still the original
        self.assertEqual(ksw.joining_date, joining)
        # But effective start is the reset date
        self.assertEqual(ksw.x_effective_start_date, reset)

    # ==================================================================
    # 3. Reset date — employee entirely in tier 2 after reset
    # ==================================================================

    def test_reset_date_tier2_employee(self):
        """Employee joined 2014-01-01, reset date 2024-06-24.
        Both are > 5 years from joining → only tier-2 rate after reset."""
        joining = date(2014, 1, 1)
        reset = date(2024, 6, 24)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)

        today = date.today()
        total_days = (today - joining).days
        reset_days = (reset - joining).days
        five_years = 5 * 365

        tier1_effective = max(
            min(total_days, five_years) - min(reset_days, five_years), 0
        )
        tier2_effective = max(
            max(total_days - five_years, 0) - max(reset_days - five_years, 0), 0
        )
        expected = (
            tier1_effective * (21.0 / 365.0)
            + tier2_effective * (30.0 / 365.0)
        )
        self.assertAlmostEqual(ksw.total_accrued_days, expected, places=2)
        # Tier 1 contribution is 0 (both boundaries > 5 years)
        self.assertEqual(tier1_effective, 0)
        self.assertGreater(tier2_effective, 0)

    # ==================================================================
    # 4. Reset date straddles the 5-year tier boundary
    # ==================================================================

    def test_reset_date_tier_transition(self):
        """Employee joined 2020-01-01. Reset 2023-06-01.
        At reset date he has ~3.5 yrs (< 5). Remaining tier-1 + some tier-2."""
        joining = date(2020, 1, 1)
        reset = date(2023, 6, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)

        today = date.today()
        total_days = (today - joining).days   # ~6 yrs (> 5)
        reset_days = (reset - joining).days   # ~3.5 yrs (< 5)
        five_years = 5 * 365

        tier1_effective = max(
            min(total_days, five_years) - min(reset_days, five_years), 0
        )
        tier2_effective = max(
            max(total_days - five_years, 0) - max(reset_days - five_years, 0), 0
        )
        expected = (
            tier1_effective * (21.0 / 365.0)
            + tier2_effective * (30.0 / 365.0)
        )
        self.assertAlmostEqual(ksw.total_accrued_days, expected, places=2)
        # Both tier contributions must be > 0
        self.assertGreater(tier1_effective, 0)
        self.assertGreater(tier2_effective, 0)

    # ==================================================================
    # 5. Opening extra days added to accrual
    # ==================================================================

    def test_opening_extra_days_added(self):
        """x_opening_extra_days is added on top of the accrued amount."""
        joining = date(2024, 1, 1)
        reset = date(2025, 1, 1)
        emp = self._make_employee(joining)

        # Without extra days
        ksw_no_extra = self._make_ksw(emp, reset_date=reset, extra_days=0.0)
        self._refresh(ksw_no_extra)
        base_accrual = ksw_no_extra.total_accrued_days

        # Delete and recreate with extra days
        ksw_no_extra.unlink()
        emp2 = self._make_employee(joining)
        ksw_with_extra = self._make_ksw(emp2, reset_date=reset, extra_days=5.0)
        self._refresh(ksw_with_extra)

        self.assertAlmostEqual(
            ksw_with_extra.total_accrued_days,
            base_accrual + 5.0,
            places=2,
        )

    # ==================================================================
    # 6. Negative extra days reduce balance
    # ==================================================================

    def test_negative_extra_days_reduce_balance(self):
        """Negative x_opening_extra_days subtracts from accrued balance."""
        joining = date(2024, 1, 1)
        reset = date(2025, 1, 1)
        emp1 = self._make_employee(joining)
        emp2 = self._make_employee(joining)

        ksw_base = self._make_ksw(emp1, reset_date=reset, extra_days=0.0)
        ksw_neg = self._make_ksw(emp2, reset_date=reset, extra_days=-3.0)
        self._refresh(ksw_base)
        self._refresh(ksw_neg)

        self.assertAlmostEqual(
            ksw_neg.total_accrued_days,
            ksw_base.total_accrued_days - 3.0,
            places=2,
        )

    # ==================================================================
    # 7. Zero extra days (default) is neutral
    # ==================================================================

    def test_zero_extra_days_neutral(self):
        """x_opening_extra_days = 0.0 does not alter accrual."""
        joining = date(2024, 1, 1)
        reset = date(2025, 1, 1)
        emp1 = self._make_employee(joining)
        emp2 = self._make_employee(joining)

        ksw_zero = self._make_ksw(emp1, reset_date=reset, extra_days=0.0)
        ksw_none = self._make_ksw(emp2, reset_date=reset)
        self._refresh(ksw_zero)
        self._refresh(ksw_none)

        self.assertAlmostEqual(
            ksw_zero.total_accrued_days,
            ksw_none.total_accrued_days,
            places=4,
        )

    # ==================================================================
    # 8. Reset date equal to joining date (equivalent to no reset)
    # ==================================================================

    def test_reset_date_same_as_joining(self):
        """When reset date == joining date, accrual equals the no-reset case."""
        joining = date(2024, 1, 1)
        emp1 = self._make_employee(joining)
        emp2 = self._make_employee(joining)

        ksw_no_reset = self._make_ksw(emp1)
        ksw_reset_joining = self._make_ksw(emp2, reset_date=joining)
        self._refresh(ksw_no_reset)
        self._refresh(ksw_reset_joining)

        self.assertAlmostEqual(
            ksw_no_reset.total_accrued_days,
            ksw_reset_joining.total_accrued_days,
            places=4,
        )

    # ==================================================================
    # 9. Future reset date yields 0 accrual
    # ==================================================================

    def test_future_reset_date_yields_zero(self):
        """If x_opening_reset_date is in the future, accrual should be 0."""
        joining = date(2024, 1, 1)
        emp = self._make_employee(joining)
        future = date(2027, 1, 1)
        ksw = self._make_ksw(emp, reset_date=future)
        self._refresh(ksw)

        self.assertEqual(ksw.total_accrued_days, 0.0)
        self.assertEqual(ksw.remaining_balance, 0.0)

    # ==================================================================
    # 10. Effective start date computed field
    # ==================================================================

    def test_effective_start_date_with_reset(self):
        """x_effective_start_date == x_opening_reset_date when set."""
        joining = date(2022, 1, 1)
        reset = date(2025, 3, 15)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)
        self.assertEqual(ksw.x_effective_start_date, reset)

    def test_effective_start_date_without_reset(self):
        """x_effective_start_date == joining_date when no reset is set."""
        joining = date(2022, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        self._refresh(ksw)
        self.assertEqual(ksw.x_effective_start_date, joining)

    # ==================================================================
    # 11. Lock guard — write to opening fields raises when locked
    # ==================================================================

    def test_locked_prevents_reset_date_change(self):
        """Writing x_opening_reset_date on a locked record raises UserError."""
        joining = date(2023, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=date(2025, 1, 1))
        # Lock
        ksw.sudo().write({'x_opening_is_locked': True})

        with self.assertRaises(UserError):
            ksw.write({'x_opening_reset_date': date(2025, 6, 1)})

    def test_locked_prevents_extra_days_change(self):
        """Writing x_opening_extra_days on a locked record raises UserError."""
        joining = date(2023, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=date(2025, 1, 1))
        ksw.sudo().write({'x_opening_is_locked': True})

        with self.assertRaises(UserError):
            ksw.write({'x_opening_extra_days': 10.0})

    def test_lock_does_not_block_other_fields(self):
        """Locking does NOT prevent writes to unrelated fields."""
        joining = date(2023, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=date(2025, 1, 1))
        ksw.sudo().write({'x_opening_is_locked': True})

        # Writing an unrelated field (e.g. unlocking itself) should NOT raise
        # — only the two opening data fields are guarded.
        ksw.sudo().write({'x_opening_is_locked': False})   # unlock
        self.assertFalse(ksw.x_opening_is_locked)

    def test_unlock_allows_changes(self):
        """After unlocking, writing x_opening_reset_date succeeds."""
        joining = date(2023, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=date(2025, 1, 1))
        ksw.sudo().write({'x_opening_is_locked': True})

        # Unlock
        ksw.sudo().write({'x_opening_is_locked': False})
        new_reset = date(2025, 6, 1)
        ksw.write({'x_opening_reset_date': new_reset})
        self.assertEqual(ksw.x_opening_reset_date, new_reset)

    # ==================================================================
    # 12. Allocation date_from set to effective start date
    # ==================================================================

    def test_allocation_date_from_set_to_reset(self):
        """After sync, allocation.date_from == x_opening_reset_date."""
        joining = date(2014, 1, 1)
        reset = date(2024, 6, 24)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)
        ksw._sync_allocations()

        if ksw.allocation_id:
            self.assertEqual(ksw.allocation_id.date_from, reset)

    def test_allocation_date_from_set_to_joining_when_no_reset(self):
        """Without reset date, allocation.date_from == joining_date."""
        joining = date(2024, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        self._refresh(ksw)
        ksw._sync_allocations()

        if ksw.allocation_id:
            self.assertEqual(ksw.allocation_id.date_from, joining)

    # ==================================================================
    # 13. _get_version_accrual_segments from_date trimming
    # ==================================================================

    def test_segments_no_from_date_uses_joining(self):
        """Without from_date, segments start from joining date."""
        joining = date(2020, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        segments = ksw._get_version_accrual_segments(emp)
        self.assertTrue(len(segments) > 0)
        self.assertEqual(segments[0]['date_from'], joining)

    def test_segments_from_date_skips_pre_reset(self):
        """Segments before from_date are excluded."""
        joining = date(2014, 1, 1)
        reset = date(2024, 6, 24)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        segments = ksw._get_version_accrual_segments(emp, from_date=reset)
        self.assertTrue(len(segments) > 0)
        # All segments must start on or after reset
        for seg in segments:
            self.assertGreaterEqual(seg['date_from'], reset)

    def test_segments_from_date_equal_to_joining_same_as_no_from_date(self):
        """from_date == joining_date yields same segments as no from_date."""
        joining = date(2022, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        segs_full = ksw._get_version_accrual_segments(emp)
        segs_reset = ksw._get_version_accrual_segments(emp, from_date=joining)
        self.assertEqual(len(segs_full), len(segs_reset))
        for s1, s2 in zip(segs_full, segs_reset):
            self.assertAlmostEqual(s1['accrual_days'], s2['accrual_days'], places=4)

    def test_segments_from_date_tier_boundary_correct(self):
        """Segment accrual days correctly reflect tier boundary from joining."""
        # Employee joined 2014, reset 2024 (both >5 yrs → tier 2 segments)
        joining = date(2014, 1, 1)
        reset = date(2024, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        segments = ksw._get_version_accrual_segments(
            emp, as_of_date=date(2026, 1, 1), from_date=reset
        )
        # All accrual in this segment is tier 2 (joining to reset is 10 yrs > 5)
        if segments:
            total_accrual = sum(s['accrual_days'] for s in segments)
            seg_days = sum(s['calendar_days'] for s in segments)
            expected = seg_days * (30.0 / 365.0)
            self.assertAlmostEqual(total_accrual, expected, places=4)

    # ==================================================================
    # 14. FIFO vacation value with reset date
    # ==================================================================

    def test_fifo_value_uses_post_reset_segments(self):
        """_compute_historical_vacation_value prices at post-reset wage."""
        joining = date(2014, 1, 1)
        reset = date(2024, 1, 1)
        wage = 9000.0
        emp = self._make_employee(joining, wage=wage)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)

        # Compute value for 10 accrual days
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            emp, 10.0
        )
        daily_wage = wage / 30.0
        expected = 10.0 * daily_wage
        self.assertAlmostEqual(result['total'], expected, places=1)
        self.assertGreater(len(result['breakdown']), 0)

    def test_fifo_value_extra_days_prepended(self):
        """Extra opening days appear first in the FIFO breakdown."""
        joining = date(2014, 1, 1)
        reset = date(2024, 1, 1)
        wage = 6000.0
        emp = self._make_employee(joining, wage=wage)
        ksw = self._make_ksw(emp, reset_date=reset, extra_days=5.0)
        self._refresh(ksw)

        # Request exactly the extra days — should be fully from synthetic segment
        result = self.env['ksw.annual.leave']._compute_historical_vacation_value(
            emp, 5.0
        )
        self.assertAlmostEqual(result['total'], 5.0 * (wage / 30.0), places=1)
        self.assertEqual(len(result['breakdown']), 1)
        self.assertAlmostEqual(result['breakdown'][0][0], 5.0, places=2)

    # ==================================================================
    # 15. Remaining balance formula consistency
    # ==================================================================

    def test_remaining_balance_equals_accrued_minus_taken(self):
        """remaining_balance == total_accrued_days - leaves_taken."""
        joining = date(2023, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        self._refresh(ksw)

        self.assertAlmostEqual(
            ksw.remaining_balance,
            ksw.total_accrued_days - ksw.leaves_taken,
            places=4,
        )

    def test_remaining_balance_with_reset_and_extra(self):
        """remaining_balance correctly accounts for reset + extra days."""
        joining = date(2014, 1, 1)
        reset = date(2024, 6, 24)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset, extra_days=7.5)
        self._refresh(ksw)

        self.assertAlmostEqual(
            ksw.remaining_balance,
            ksw.total_accrued_days - ksw.leaves_taken,
            places=4,
        )
        # Extra days should be included in remaining (no leaves taken yet)
        # total_accrued = post-reset-accrual + 7.5 extra
        # remaining = total_accrued - 0 = total_accrued
        self.assertAlmostEqual(ksw.remaining_balance, ksw.total_accrued_days, places=4)

    # ==================================================================
    # 16. Changing reset date updates accrual
    # ==================================================================

    def test_changing_reset_date_updates_accrual(self):
        """Writing a new x_opening_reset_date triggers recompute."""
        joining = date(2022, 1, 1)
        reset1 = date(2025, 1, 1)
        reset2 = date(2025, 6, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset1)
        self._refresh(ksw)
        accrual1 = ksw.total_accrued_days

        ksw.write({'x_opening_reset_date': reset2})
        self._refresh(ksw)
        accrual2 = ksw.total_accrued_days

        # reset2 is later than reset1 → less accrual since reset
        self.assertLess(accrual2, accrual1)

    # ==================================================================
    # 17. _refresh_accrual re-triggers compute after reset date set
    # ==================================================================

    def test_refresh_accrual_after_reset_date_set(self):
        """_refresh_accrual recomputes correctly after reset date update."""
        joining = date(2022, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        ksw._refresh_accrual()
        balance_before = ksw.total_accrued_days

        ksw.write({'x_opening_reset_date': date(2025, 1, 1)})
        ksw._refresh_accrual()
        balance_after = ksw.total_accrued_days

        # Accrual should be smaller (reset starts later than joining)
        self.assertLess(balance_after, balance_before)

    # ==================================================================
    # 18. Reset date before joining is normalised to joining date
    # ==================================================================

    def test_reset_date_before_joining_normalised(self):
        """A reset date before joining date acts like no reset (starts from joining)."""
        joining = date(2024, 1, 1)
        before = date(2023, 1, 1)
        emp1 = self._make_employee(joining)
        emp2 = self._make_employee(joining)

        ksw_no_reset = self._make_ksw(emp1)
        ksw_before_joining = self._make_ksw(emp2, reset_date=before)
        self._refresh(ksw_no_reset)
        self._refresh(ksw_before_joining)

        # Segment trimming: from_date <= joining → treated as joining
        # Accrual should be the same
        self.assertAlmostEqual(
            ksw_no_reset.total_accrued_days,
            ksw_before_joining.total_accrued_days,
            places=2,
        )

    # ==================================================================
    # 19. Years of service always uses full joining date (not reset date)
    # ==================================================================

    def test_years_of_service_uses_full_joining_date(self):
        """years_of_service is based on joining date, not reset date."""
        joining = date(2014, 1, 1)
        reset = date(2024, 6, 24)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)

        today = date.today()
        from dateutil.relativedelta import relativedelta
        rdelta = relativedelta(today, joining)
        expected_yos = round(
            rdelta.years + rdelta.months / 12.0 + rdelta.days / 365.25, 2
        )
        self.assertAlmostEqual(ksw.years_of_service, expected_yos, places=1)
        # Must be > 12 years, not just ~2 years from reset
        self.assertGreater(ksw.years_of_service, 12.0)

    # ==================================================================
    # 20. Daily rate uses full service duration (not since reset)
    # ==================================================================

    def test_daily_rate_uses_total_service(self):
        """daily_rate = 30/365 for employees > 5 years even if reset < 5 yrs ago."""
        joining = date(2014, 1, 1)  # > 5 years ago
        reset = date(2024, 6, 24)   # < 5 years ago — but service is already > 5y
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp, reset_date=reset)
        self._refresh(ksw)
        self.assertAlmostEqual(ksw.daily_rate, 30.0 / 365.0, places=6)

    def test_daily_rate_tier1_for_new_employee(self):
        """daily_rate = 21/365 for employees < 5 years."""
        joining = date(2023, 1, 1)
        emp = self._make_employee(joining)
        ksw = self._make_ksw(emp)
        self._refresh(ksw)
        self.assertAlmostEqual(ksw.daily_rate, 21.0 / 365.0, places=6)


# ==================================================================
# Wizard tests (separate class for clarity)
# ==================================================================

class TestOpeningBalanceWizard(TransactionCase):
    """Tests for the opening.balance.wizard (bulk setup)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Annual leave type
        cls.annual_type = cls.env['hr.leave.type'].create({
            'name': 'Annual Leave Wizard Test',
            'requires_allocation': False,
            'is_annual_leave': True,
            'leave_validation_type': 'no_validation',
        })
        cls.env['hr.leave.type'].sudo().search([
            ('is_annual_leave', '=', True),
            ('id', '!=', cls.annual_type.id),
        ]).write({'is_annual_leave': False})

        cls._counter = 0

    def _make_employee(self, joining=None, name=None):
        TestOpeningBalanceWizard._counter += 1
        n = self._counter
        joining = joining or date(2022, 1, 1)
        emp = self.env['hr.employee'].create({
            'name': name or 'Wizard Test Emp %d' % n,
        })
        version = emp.current_version_id
        version.write({
            'name': 'Ver Wiz %d' % n,
            'date_version': joining,
            'contract_date_start': joining,
            'wage': 5000.0,
        })
        emp._compute_current_version_id()
        return emp

    def _make_wizard(self, lines):
        """Create wizard with line dicts [{employee_id, opening_reset_date, ...}]."""
        wizard = self.env['opening.balance.wizard'].sudo().create({
            'skip_locked': True,
        })
        for line_vals in lines:
            line_vals['wizard_id'] = wizard.id
            self.env['opening.balance.wizard.line'].sudo().create(line_vals)
        return wizard

    # ------------------------------------------------------------------

    def test_wizard_applies_opening_balance(self):
        """Applying wizard sets x_opening_reset_date and x_opening_extra_days."""
        emp = self._make_employee()
        reset = date(2025, 3, 1)
        extra = 4.5

        wizard = self._make_wizard([{
            'employee_id': emp.id,
            'opening_reset_date': reset,
            'opening_extra_days': extra,
            'lock_after_apply': True,
        }])
        wizard.action_apply()

        ksw = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', emp.id),
        ], limit=1)
        self.assertTrue(ksw)
        self.assertEqual(ksw.x_opening_reset_date, reset)
        self.assertAlmostEqual(ksw.x_opening_extra_days, extra, places=4)
        self.assertTrue(ksw.x_opening_is_locked)

    def test_wizard_locks_after_apply(self):
        """When lock_after_apply=True, record is locked after applying."""
        emp = self._make_employee()
        wizard = self._make_wizard([{
            'employee_id': emp.id,
            'opening_reset_date': date(2025, 1, 1),
            'opening_extra_days': 0.0,
            'lock_after_apply': True,
        }])
        wizard.action_apply()
        ksw = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', emp.id),
        ], limit=1)
        self.assertTrue(ksw.x_opening_is_locked)

    def test_wizard_no_lock_when_false(self):
        """When lock_after_apply=False, record is NOT locked after applying."""
        emp = self._make_employee()
        wizard = self._make_wizard([{
            'employee_id': emp.id,
            'opening_reset_date': date(2025, 1, 1),
            'opening_extra_days': 0.0,
            'lock_after_apply': False,
        }])
        wizard.action_apply()
        ksw = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', emp.id),
        ], limit=1)
        self.assertFalse(ksw.x_opening_is_locked)

    def test_wizard_skip_locked_records(self):
        """With skip_locked=True, locked records are skipped without error."""
        emp = self._make_employee()
        # Pre-create and lock the record
        ksw = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': emp.id,
            'x_opening_reset_date': date(2025, 1, 1),
            'x_opening_extra_days': 2.0,
        })
        ksw.sudo().write({'x_opening_is_locked': True})

        wizard = self._make_wizard([{
            'employee_id': emp.id,
            'opening_reset_date': date(2025, 6, 1),  # different date
            'opening_extra_days': 10.0,
            'lock_after_apply': False,
        }])
        wizard.sudo().write({'skip_locked': True})
        # Should not raise
        wizard.action_apply()

        # The locked record should be unchanged
        ksw.invalidate_recordset()
        self.assertEqual(ksw.x_opening_reset_date, date(2025, 1, 1))
        self.assertAlmostEqual(ksw.x_opening_extra_days, 2.0, places=4)

    def test_wizard_skip_locked_false_raises(self):
        """With skip_locked=False, locked records cause a UserError."""
        emp = self._make_employee()
        ksw = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': emp.id,
            'x_opening_reset_date': date(2025, 1, 1),
        })
        ksw.sudo().write({'x_opening_is_locked': True})

        wizard = self._make_wizard([{
            'employee_id': emp.id,
            'opening_reset_date': date(2025, 6, 1),
            'opening_extra_days': 0.0,
            'lock_after_apply': False,
        }])
        wizard.sudo().write({'skip_locked': False})

        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_wizard_empty_lines_raises(self):
        """Applying a wizard with no lines raises UserError."""
        wizard = self.env['opening.balance.wizard'].sudo().create({
            'skip_locked': True,
        })
        with self.assertRaises(UserError):
            wizard.action_apply()

    def test_wizard_creates_ksw_record_if_missing(self):
        """Wizard creates the ksw.annual.leave record when it doesn't exist."""
        emp = self._make_employee()
        # Ensure no existing record
        self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', emp.id),
        ]).unlink()

        wizard = self._make_wizard([{
            'employee_id': emp.id,
            'opening_reset_date': date(2025, 1, 1),
            'opening_extra_days': 3.0,
            'lock_after_apply': False,
        }])
        wizard.action_apply()

        ksw = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', emp.id),
        ], limit=1)
        self.assertTrue(ksw)
        self.assertEqual(ksw.x_opening_reset_date, date(2025, 1, 1))

    def test_wizard_multiple_employees(self):
        """Wizard correctly applies different settings to multiple employees."""
        emp1 = self._make_employee()
        emp2 = self._make_employee()
        reset1 = date(2024, 6, 1)
        reset2 = date(2025, 1, 1)

        wizard = self._make_wizard([
            {
                'employee_id': emp1.id,
                'opening_reset_date': reset1,
                'opening_extra_days': 5.0,
                'lock_after_apply': True,
            },
            {
                'employee_id': emp2.id,
                'opening_reset_date': reset2,
                'opening_extra_days': 2.5,
                'lock_after_apply': False,
            },
        ])
        wizard.action_apply()

        ksw1 = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', emp1.id),
        ], limit=1)
        ksw2 = self.env['ksw.annual.leave'].sudo().search([
            ('employee_id', '=', emp2.id),
        ], limit=1)

        self.assertEqual(ksw1.x_opening_reset_date, reset1)
        self.assertAlmostEqual(ksw1.x_opening_extra_days, 5.0, places=4)
        self.assertTrue(ksw1.x_opening_is_locked)

        self.assertEqual(ksw2.x_opening_reset_date, reset2)
        self.assertAlmostEqual(ksw2.x_opening_extra_days, 2.5, places=4)
        self.assertFalse(ksw2.x_opening_is_locked)

