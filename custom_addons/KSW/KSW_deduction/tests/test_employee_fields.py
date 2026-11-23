# -*- coding: utf-8 -*-
"""Tests for hr.employee custom fields and action_view_deductions."""
from datetime import date
from dateutil.relativedelta import relativedelta
from .common import DeductionCommon
class TestEmployeeFields(DeductionCommon):
    def test_count_only_active_deductions(self):
        # 2 active + 1 cancelled
        d_active1 = self._make_deduction(amount=100.0, installments=1)
        d_active1.action_submit()
        d_active2 = self._make_deduction(amount=200.0, installments=2)
        d_active2.action_submit()
        d_cancel = self._make_deduction(amount=50.0, installments=1)
        d_cancel.action_submit()
        d_cancel.action_cancel()
        self.employee.invalidate_recordset(['x_deduction_count',
                                            'x_deduction_monthly_total',
                                            'x_deduction_currency_id'])
        self.assertEqual(self.employee.x_deduction_count, 2)
        self.assertEqual(self.employee.x_deduction_currency_id,
                         self.company.currency_id)
    def test_monthly_total_filters_current_month(self):
        # Current-month line counted
        d_curr = self._make_deduction(amount=100.0, installments=1,
                                      start_month=self.this_month)
        d_curr.action_submit()
        # Next-month line not counted
        d_next = self._make_deduction(amount=999.0, installments=1,
                                      start_month=self.next_month)
        d_next.action_submit()
        self.employee.invalidate_recordset(['x_deduction_monthly_total'])
        self.assertEqual(self.employee.x_deduction_monthly_total, 100.0)
    def test_monthly_total_excludes_paid_and_skipped(self):
        d = self._make_deduction(amount=300.0, installments=3,
                                 start_month=self.this_month)
        d.action_submit()
        # Mark first (current month) line as paid → excluded
        curr_line = d.line_ids.filtered(
            lambda l: l.period_date == self.this_month)
        curr_line.write({'state': 'paid'})
        self.employee.invalidate_recordset(['x_deduction_monthly_total'])
        self.assertEqual(self.employee.x_deduction_monthly_total, 0.0)
    def test_action_view_deductions_returns_action(self):
        action = self.employee.action_view_deductions()
        self.assertEqual(action['res_model'], 'ksw.deduction')
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['domain'], [('employee_id', '=', self.employee.id)])
        self.assertEqual(action['context']['default_employee_id'], self.employee.id)
        self.assertIn('list', action['view_mode'])
        self.assertIn('form', action['view_mode'])
