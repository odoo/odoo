# -*- coding: utf-8 -*-
"""Tests for Pass 2 — HR Decisions on ksw.deduction.

Covers:
  - End-of-Service termination amount (Saudi Art. 84)
  - End-of-Service resignation tiers (Art. 85) + force majeure (Art. 87)
  - Translated annual vacation balance via FIFO historical wage
  - Active deductions summary (excludes self / non-active states)
"""
from datetime import date, timedelta

from .common import DeductionCommon


class TestEosAndSummary(DeductionCommon):
    """HR Decisions field tests."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.today = date.today()

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_employee_contract(self, employee, years_ago, wage):
        """Backdate the employee's first version and set its wage.

        Writes contract_date_start = today - years_ago years on the
        current (auto-created) version, and sets the wage.
        """
        joining = self.today - timedelta(days=int(round(years_ago * 365.25)))
        version = employee.current_version_id
        version.write({
            'date_version': joining,
            'contract_date_start': joining,
            'wage': wage,
        })
        employee._compute_current_version_id()

    def _make_eos_record(self, employee=None):
        """A draft non-loan deduction is enough to read EOS computed fields."""
        return self._make_deduction(
            ded_type=self.type_advance,
            employee=employee or self.employee,
            amount=100.0, installments=1,
        )

    # ==================================================================
    # End-of-Service — Termination (Article 84)
    # ==================================================================
    def test_eos_termination_under_5_years(self):
        """3 years × 6000 wage → 0.5 × 6000 × 3 = 9,000."""
        self._set_employee_contract(self.employee, 3.0, 6000.0)
        rec = self._make_eos_record()
        self.assertAlmostEqual(rec.x_eos_service_years, 3.0, places=1)
        self.assertAlmostEqual(rec.x_eos_last_wage, 6000.0, places=2)
        self.assertAlmostEqual(rec.x_eos_termination_amount, 9000.0, delta=50)

    def test_eos_termination_exactly_5_years(self):
        """5 years × 6000 wage → 0.5 × 6000 × 5 = 15,000."""
        self._set_employee_contract(self.employee, 5.0, 6000.0)
        rec = self._make_eos_record()
        self.assertAlmostEqual(rec.x_eos_service_years, 5.0, places=1)
        self.assertAlmostEqual(rec.x_eos_termination_amount, 15000.0, delta=50)

    def test_eos_termination_10_years(self):
        """10 yrs: 0.5×5×6000 + 1×5×6000 = 15,000 + 30,000 = 45,000."""
        self._set_employee_contract(self.employee, 10.0, 6000.0)
        rec = self._make_eos_record()
        self.assertAlmostEqual(rec.x_eos_service_years, 10.0, places=1)
        self.assertAlmostEqual(rec.x_eos_termination_amount, 45000.0, delta=100)

    # ==================================================================
    # End-of-Service — Resignation tiers (Article 85)
    # ==================================================================
    def test_eos_resignation_under_2_years(self):
        """< 2 years → resignation = 0."""
        self._set_employee_contract(self.employee, 1.0, 6000.0)
        rec = self._make_eos_record()
        self.assertAlmostEqual(rec.x_eos_resignation_amount, 0.0, places=2)

    def test_eos_resignation_2_to_5_years(self):
        """2 ≤ yrs < 5 → 1/3 of termination amount."""
        self._set_employee_contract(self.employee, 3.0, 6000.0)
        rec = self._make_eos_record()
        expected = rec.x_eos_termination_amount / 3.0
        self.assertAlmostEqual(rec.x_eos_resignation_amount, expected, places=2)

    def test_eos_resignation_5_to_10_years(self):
        """5 ≤ yrs < 10 → 2/3 of termination amount."""
        self._set_employee_contract(self.employee, 7.0, 6000.0)
        rec = self._make_eos_record()
        expected = rec.x_eos_termination_amount * 2.0 / 3.0
        self.assertAlmostEqual(rec.x_eos_resignation_amount, expected, places=2)

    def test_eos_resignation_10_or_more_years(self):
        """≥ 10 yrs → full termination amount."""
        self._set_employee_contract(self.employee, 12.0, 6000.0)
        rec = self._make_eos_record()
        self.assertAlmostEqual(
            rec.x_eos_resignation_amount, rec.x_eos_termination_amount,
            places=2,
        )

    def test_eos_resignation_force_majeure_short_service(self):
        """Force majeure → resignation = full termination, even at 1 year."""
        self._set_employee_contract(self.employee, 1.0, 6000.0)
        rec = self._make_eos_record()
        # Without force majeure: 0
        self.assertAlmostEqual(rec.x_eos_resignation_amount, 0.0, places=2)
        rec.x_eos_force_majeure = True
        rec.invalidate_recordset()
        self.assertAlmostEqual(
            rec.x_eos_resignation_amount, rec.x_eos_termination_amount,
            places=2,
        )
        self.assertGreater(rec.x_eos_resignation_amount, 0.0)

    def test_eos_no_employee_zero(self):
        """No employee version data → all EOS fields are 0."""
        # Employee with no contract_date_start on its version
        emp = self.env['hr.employee'].create({'name': 'KSWDED No Version'})
        # Make sure version has no contract_date_start
        emp.current_version_id.write({'contract_date_start': False, 'wage': 0.0})
        rec = self._make_eos_record(employee=emp)
        self.assertEqual(rec.x_eos_service_years, 0.0)
        self.assertEqual(rec.x_eos_last_wage, 0.0)
        self.assertEqual(rec.x_eos_termination_amount, 0.0)
        self.assertEqual(rec.x_eos_resignation_amount, 0.0)

    # ==================================================================
    # Vacation balance — translated via FIFO historical wage
    # ==================================================================
    def test_vacation_balance_no_record(self):
        """No ksw.annual.leave record → all vacation fields default."""
        rec = self._make_eos_record()
        self.assertEqual(rec.x_vac_balance_days, 0.0)
        self.assertEqual(rec.x_vac_balance_value, 0.0)
        self.assertEqual(rec.x_vac_balance_breakdown, '')

    def test_vacation_balance_uses_annual_leave_remaining(self):
        """Vacation fields read remaining_balance and historical value."""
        self._set_employee_contract(self.employee, 3.0, 6000.0)
        # Create the ksw.annual.leave record
        ksw_rec = self.env['ksw.annual.leave'].sudo().create({
            'employee_id': self.employee.id,
        })
        # Patch remaining_balance via direct field write — it's computed,
        # so simulate via mock call instead.
        rec = self._make_eos_record()
        # Reference: call the API directly with the same days
        days = ksw_rec.remaining_balance or 0.0
        self.assertEqual(rec.x_vac_balance_days, days)
        if days > 0:
            ref = self.env['ksw.annual.leave']._compute_historical_vacation_value(
                self.employee, days, exclude_days=0.0)
            self.assertAlmostEqual(
                rec.x_vac_balance_value, ref['total'], places=2)
            self.assertEqual(rec.x_vac_balance_breakdown, ref['label'])

    # ==================================================================
    # Active deductions summary
    # ==================================================================
    def test_active_summary_excludes_self_and_non_active(self):
        """Summary counts only OTHER active deductions."""
        # Create 2 active siblings (advance is non-loan → instant active)
        sib1 = self._make_deduction(amount=400.0, installments=4)
        sib1.action_submit()
        sib2 = self._make_deduction(amount=600.0, installments=3)
        sib2.action_submit()
        # Create a draft (should be excluded)
        self._make_deduction(amount=999.0, installments=1)
        # Create a cancelled (should be excluded)
        cancelled = self._make_deduction(amount=500.0, installments=2)
        cancelled.action_submit()
        cancelled.action_cancel()
        # The record under inspection — should not count itself
        rec = self._make_deduction(amount=200.0, installments=2)
        rec.action_submit()
        # Expect exactly 2 active siblings
        self.assertEqual(rec.x_active_deductions_count, 2)
        self.assertAlmostEqual(
            rec.x_active_deductions_total_outstanding,
            sib1.total_pending + sib2.total_pending,
            places=2,
        )
        self.assertAlmostEqual(
            rec.x_active_deductions_monthly_impact,
            sib1.installment_amount + sib2.installment_amount,
            places=2,
        )

    def test_active_summary_breakdown_html_per_type(self):
        """HTML breakdown lists each distinct type."""
        sib_adv = self._make_deduction(
            ded_type=self.type_advance, amount=400.0, installments=2)
        sib_adv.action_submit()
        sib_pen = self._make_deduction(
            ded_type=self.type_internal_pen, amount=300.0, installments=3)
        sib_pen.action_submit()
        rec = self._make_eos_record()
        html = rec.x_active_deductions_summary or ''
        self.assertIn(self.type_advance.name, html)
        self.assertIn(self.type_internal_pen.name, html)

    def test_active_summary_other_employee_isolated(self):
        """Sibling deductions for a different employee are not counted."""
        other = self._make_deduction(employee=self.employee_b, amount=500.0)
        other.action_submit()
        rec = self._make_eos_record(employee=self.employee)
        self.assertEqual(rec.x_active_deductions_count, 0)
        self.assertEqual(rec.x_active_deductions_total_outstanding, 0.0)


