# -*- coding: utf-8 -*-
"""Tests for hr.payslip integration: input injection, sync on done/reset, salary rule."""
from datetime import date
from dateutil.relativedelta import relativedelta
from .common import DeductionCommon
class TestDeductionPayslip(DeductionCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Build a working calendar so the employee has a valid version for
        # om_hr_payroll computations.
        cls.calendar_group = cls.env['resource.calendar.group'].create({
            'name': 'KSWDED Sched',
        })
        for day in ['0', '1', '2', '3', '6']:
            cls.env['resource.calendar.group.line'].create({
                'name': f'd{day}',
                'calendar_group_id': cls.calendar_group.id,
                'dayofweek': day,
                'day_period': 'full_day',
                'hour_from': 8.0,
                'hour_to': 16.5,
            })
        cls.calendar = cls.env['resource.calendar'].create({
            'name': 'KSWDED Cal',
            'tz': 'Asia/Riyadh',
            'calendar_group_ids': [(4, cls.calendar_group.id)],
        })
        cls.employee.write({'resource_calendar_id': cls.calendar.id})
        cls.struct = cls.env.ref('om_hr_payroll.structure_base')
        cls.version = cls.employee.current_version_id
        cls.version.write({
            'name': 'KSWDED Version',
            'date_version': date(2025, 1, 1),
            'contract_date_start': date(2025, 1, 1),
            'resource_calendar_id': cls.calendar.id,
            'wage': 6000.0,
            'da': 0.0,
            'travel_allowance': 0.0,
            'meal_allowance': 0.0,
            'medical_allowance': 0.0,
            'other_allowance': 0.0,
            'hra': 0.0,
            'struct_id': cls.struct.id,
        })
        cls.employee._compute_current_version_id()
        cls.period_from = date(2026, 4, 1)
        cls.period_to = date(2026, 4, 30)
    def _make_payslip(self, employee=None, dfrom=None, dto=None, name='Slip'):
        return self.env['hr.payslip'].create({
            'employee_id': (employee or self.employee).id,
            'name': name,
            'date_from': dfrom or self.period_from,
            'date_to': dto or self.period_to,
            'struct_id': self.struct.id,
            'version_id': self.version.id,
        })
    def _ksw_inputs(self, slip):
        return slip.input_line_ids.filtered(
            lambda i: i.code and i.code.startswith('KSW_DED_'))
    # ------------------------------------------------------------------
    # Input injection
    # ------------------------------------------------------------------
    def test_inputs_injected_for_lines_in_period(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=300.0, installments=3,
                                   start_month=date(2026, 3, 1))
        ded.action_submit()
        # Lines: Mar/Apr/May ; payslip Apr should pick the Apr line only
        slip = self._make_payslip()
        slip.compute_sheet()
        inputs = self._ksw_inputs(slip)
        self.assertEqual(len(inputs), 1)
        inp = inputs[0]
        self.assertEqual(inp.amount, 100.0)
        apr_line = ded.line_ids.filtered(
            lambda l: l.period_date == date(2026, 4, 1))
        self.assertEqual(inp.code, f'KSW_DED_{apr_line.id}')
        self.assertEqual(inp.version_id, self.version)
        self.assertGreaterEqual(inp.sequence, 50)
        self.assertIn('inst 2/3', inp.name)
        self.assertIn(ded.name, inp.name)
        self.assertIn(ded.type_id.name, inp.name)
    def test_inputs_skipped_for_lines_outside_period(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=200.0, installments=2,
                                   start_month=date(2026, 6, 1))
        ded.action_submit()
        slip = self._make_payslip()  # April
        slip.compute_sheet()
        self.assertFalse(self._ksw_inputs(slip))
    def test_inputs_skipped_for_other_employees(self):
        ded = self._make_deduction(self.type_advance, employee=self.employee_b,
                                   amount=100.0, installments=1,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        slip = self._make_payslip(employee=self.employee)
        slip.compute_sheet()
        self.assertFalse(self._ksw_inputs(slip))
    def test_inputs_skipped_when_deduction_not_active(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=100.0, installments=1,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        ded.action_cancel()  # state -> cancelled, lines -> skipped
        slip = self._make_payslip()
        slip.compute_sheet()
        self.assertFalse(self._ksw_inputs(slip))
    def test_inputs_skipped_for_paid_or_skipped_lines(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=200.0, installments=2,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        # Mark the April line as paid manually, leave May pending
        ded.line_ids.filtered(
            lambda l: l.month == 4).write({'state': 'paid'})
        slip = self._make_payslip()
        slip.compute_sheet()
        self.assertFalse(self._ksw_inputs(slip))
    def test_recompute_replaces_inputs(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=200.0, installments=2,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        slip = self._make_payslip()
        slip.compute_sheet()
        inputs1 = self._ksw_inputs(slip)
        self.assertEqual(len(inputs1), 1)
        first_id = inputs1.id
        # Change line amount, recompute → old input removed, new one created
        ded.line_ids.filtered(lambda l: l.month == 4).write({'amount': 175.0})
        slip.compute_sheet()
        inputs2 = self._ksw_inputs(slip)
        self.assertEqual(len(inputs2), 1)
        self.assertNotEqual(inputs2.id, first_id)
        self.assertEqual(inputs2.amount, 175.0)
    # ------------------------------------------------------------------
    # Salary rule integration
    # ------------------------------------------------------------------
    def test_salary_rule_aggregates_negative_total(self):
        # Two active deductions with lines in April
        d1 = self._make_deduction(self.type_advance,
                                  amount=100.0, installments=1,
                                  start_month=date(2026, 4, 1))
        d1.action_submit()
        d2 = self._make_deduction(self.type_gov_pen,
                                  amount=250.0, installments=1,
                                  start_month=date(2026, 4, 1))
        d2.action_submit()
        slip = self._make_payslip()
        slip.compute_sheet()
        ded_line = slip.line_ids.filtered(lambda l: l.code == 'KSW_DEDUCTIONS')
        self.assertEqual(len(ded_line), 1)
        self.assertEqual(ded_line.total, -350.0)
    def test_no_rule_line_when_no_inputs(self):
        slip = self._make_payslip()
        slip.compute_sheet()
        ded_line = slip.line_ids.filtered(lambda l: l.code == 'KSW_DEDUCTIONS')
        self.assertFalse(ded_line)
    # ------------------------------------------------------------------
    # Sync on state transitions
    # ------------------------------------------------------------------
    def test_done_marks_lines_paid(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=200.0, installments=2,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertEqual(slip.state, 'done')
        apr_line = ded.line_ids.filtered(lambda l: l.month == 4)
        self.assertEqual(apr_line.state, 'paid')
        self.assertEqual(apr_line.payslip_id, slip)
        # The May line is untouched
        may_line = ded.line_ids.filtered(lambda l: l.month == 5)
        self.assertEqual(may_line.state, 'pending')
    def test_done_auto_completes_when_all_paid(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=100.0, installments=1,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertEqual(ded.state, 'completed')
        # Chatter contains "Completed"
        bodies = ded.message_ids.mapped('body')
        self.assertTrue(any('Completed' in (b or '') for b in bodies))
    def test_done_does_not_complete_when_lines_remain(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=200.0, installments=2,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertEqual(ded.state, 'active')
    def test_reset_to_draft_unmarks_lines(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=100.0, installments=1,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        self.assertEqual(ded.state, 'completed')
        # Move slip back to draft
        slip.write({'state': 'draft'})
        line = ded.line_ids
        self.assertEqual(line.state, 'pending')
        self.assertFalse(line.payslip_id)
        # Auto-completed deduction was re-opened to active
        self.assertEqual(ded.state, 'active')
    def test_cancel_payslip_unmarks_lines(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=100.0, installments=1,
                                   start_month=date(2026, 4, 1))
        ded.action_submit()
        slip = self._make_payslip()
        slip.compute_sheet()
        slip.action_payslip_done()
        slip.write({'state': 'cancel'})
        line = ded.line_ids
        self.assertEqual(line.state, 'pending')
        self.assertFalse(line.payslip_id)
    def test_done_noop_without_ksw_inputs(self):
        slip = self._make_payslip()
        slip.compute_sheet()
        # No deductions exist → should transition cleanly
        slip.action_payslip_done()
        self.assertEqual(slip.state, 'done')
    def test_malformed_input_code_ignored(self):
        # Simulate a stray non-numeric KSW_DED_ input → should not crash
        slip = self._make_payslip()
        self.env['hr.payslip.input'].create({
            'payslip_id': slip.id,
            'version_id': self.version.id,
            'name': 'Stray',
            'code': 'KSW_DED_xyz',
            'amount': 0.0,
            'sequence': 99,
        })
        # This should not raise
        slip._sync_deductions_on_done(slip)
