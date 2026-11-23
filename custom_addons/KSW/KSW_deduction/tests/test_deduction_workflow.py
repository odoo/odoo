# -*- coding: utf-8 -*-
"""Tests for ksw.deduction lifecycle, sequence, validations, loan workflow."""
from datetime import date, datetime
from psycopg2 import IntegrityError
from odoo.exceptions import UserError, ValidationError
from odoo.tools import mute_logger
from .common import DeductionCommon
class TestDeductionWorkflow(DeductionCommon):
    # ------------------------------------------------------------------
    # Sequence / defaults / computed
    # ------------------------------------------------------------------
    def test_sequence_generated_on_create(self):
        ded = self._make_deduction()
        self.assertTrue(ded.name.startswith('KSWDED/'),
                        f'Expected KSWDED prefix, got {ded.name!r}')
        self.assertNotEqual(ded.name, 'New')
    def test_sequence_replaces_default_new(self):
        ded = self.env['ksw.deduction'].create({
            'employee_id': self.employee.id,
            'type_id': self.type_advance.id,
            'amount': 100.0,
            'installments': 1,
            'name': 'New',
        })
        self.assertNotEqual(ded.name, 'New')
    def test_explicit_name_preserved(self):
        ded = self.env['ksw.deduction'].create({
            'employee_id': self.employee.id,
            'type_id': self.type_advance.id,
            'amount': 100.0,
            'installments': 1,
            'name': 'MANUAL/1',
        })
        self.assertEqual(ded.name, 'MANUAL/1')
    def test_default_state_and_related(self):
        ded = self._make_deduction(self.type_loan)
        self.assertEqual(ded.state, 'draft')
        self.assertFalse(ded.approval_state)
        self.assertEqual(ded.currency_id, self.company.currency_id)
        self.assertEqual(ded.start_month, self.this_month)
        self.assertEqual(ded.category, 'borrowed')
        self.assertTrue(ded.is_loan)
        self.assertEqual(ded.department_id, self.dept_a)
        self.assertEqual(ded.manager_id, self.manager_emp)
    def test_compute_installment_amount(self):
        ded = self._make_deduction(amount=1000.0, installments=4)
        self.assertEqual(ded.installment_amount, 250.0)
        ded.write({'amount': 0.0})
        self.assertEqual(ded.installment_amount, 0.0)
        ded.write({'amount': 500.0, 'installments': 0})
        self.assertEqual(ded.installment_amount, 0.0)
    def test_onchange_type_sets_default_installments(self):
        from odoo.tests import Form
        with Form(self.env['ksw.deduction']) as f:
            f.employee_id = self.employee
            f.type_id = self.type_loan
            f.amount = 1000.0
            self.assertEqual(f.installments, 10)
            f.type_id = self.type_advance
            self.assertEqual(f.installments, 1)
    # ------------------------------------------------------------------
    # Submit / validations
    # ------------------------------------------------------------------
    def test_submit_non_loan_instant_active(self):
        ded = self._make_deduction(self.type_advance,
                                   amount=500.0, installments=2)
        ded.action_submit()
        self.assertEqual(ded.state, 'active')
        self.assertFalse(ded.approval_state)
        self.assertEqual(len(ded.line_ids), 2)
        self.assertEqual(sum(ded.line_ids.mapped('amount')), 500.0)
        self.assertTrue(all(l.state == 'pending' for l in ded.line_ids))
        self.assertEqual(ded.line_ids.mapped('sequence'), [1, 2])
    def test_submit_loan_enters_pending_dm(self):
        ded = self._make_deduction(self.type_loan)
        ded.action_submit()
        self.assertEqual(ded.state, 'draft')
        self.assertEqual(ded.approval_state, 'pending_dm')
        self.assertFalse(ded.line_ids)
    def test_submit_zero_amount_raises(self):
        ded = self._make_deduction(amount=0.0)
        with self.assertRaises(ValidationError):
            ded.action_submit()
    def test_submit_zero_installments_raises(self):
        ded = self._make_deduction(installments=0)
        with self.assertRaises(ValidationError):
            ded.action_submit()
    def test_resubmit_active_raises(self):
        ded = self._make_deduction()
        ded.action_submit()
        with self.assertRaises(UserError):
            ded.action_submit()
    # ------------------------------------------------------------------
    # Loan approval chain
    # ------------------------------------------------------------------
    def test_full_loan_approval_chain(self):
        ded = self._make_deduction(self.type_loan,
                                   amount=2000.0, installments=4)
        ded.action_submit()
        ded.action_dm_approve()
        self.assertEqual(ded.approval_state, 'pending_hr')
        self.assertTrue(ded.dm_approved_date)
        ded.x_hr_no_penalties_confirmed = True
        ded.action_hr_approve()
        self.assertEqual(ded.approval_state, 'pending_acc')
        self.assertTrue(ded.hr_approved_date)
        # Accountant snapshot captured on entry to pending_acc
        self.assertEqual(ded.acc_original_amount, 2000.0)
        self.assertEqual(ded.acc_original_installments, 4)
        ded.x_acc_budget_confirmed = True
        ded.action_acc_approve()
        self.assertEqual(ded.approval_state, 'pending_gm')
        self.assertTrue(ded.acc_approved_date)
        # GM snapshot captured
        self.assertEqual(ded.gm_original_amount, 2000.0)
        self.assertEqual(ded.gm_original_installments, 4)
        ded.action_gm_approve()
        self.assertEqual(ded.approval_state, 'approved')
        self.assertEqual(ded.state, 'active')
        self.assertEqual(len(ded.line_ids), 4)
        self.assertTrue(ded.gm_approved_date)
    def test_loan_step_order_enforced(self):
        ded = self._make_deduction(self.type_loan)
        ded.action_submit()  # pending_dm
        with self.assertRaises(UserError):
            ded.action_hr_approve()
        with self.assertRaises(UserError):
            ded.action_acc_approve()
        with self.assertRaises(UserError):
            ded.action_gm_approve()
        ded.action_dm_approve()  # pending_hr
        with self.assertRaises(UserError):
            ded.action_dm_approve()
        with self.assertRaises(UserError):
            ded.action_acc_approve()
    def test_loan_actions_blocked_for_non_loan(self):
        ded = self._make_deduction(self.type_advance)
        with self.assertRaises(UserError):
            ded.action_dm_approve()
        with self.assertRaises(UserError):
            ded.action_hr_approve()
        with self.assertRaises(UserError):
            ded.action_acc_approve()
        with self.assertRaises(UserError):
            ded.action_gm_approve()
    def test_gm_modification_logged(self):
        ded = self._make_deduction(self.type_loan,
                                   amount=1000.0, installments=10)
        self._walk_loan_to_pending_gm(ded)
        # GM modifies
        ded.write({'amount': 800.0, 'installments': 8})
        ded.action_gm_approve()
        self.assertEqual(ded.state, 'active')
        self.assertEqual(len(ded.line_ids), 8)
        self.assertEqual(sum(ded.line_ids.mapped('amount')), 800.0)
        # Chatter contains modification log
        msgs = ded.message_ids.mapped('body')
        self.assertTrue(any('Modifications' in (m or '') for m in msgs))
        self.assertTrue(any('1000.00' in (m or '') and '800.00' in (m or '')
                            for m in msgs))
    def test_gm_no_modification_no_log(self):
        ded = self._make_deduction(self.type_loan,
                                   amount=1000.0, installments=4)
        self._walk_loan_to_pending_gm(ded)
        ded.action_gm_approve()
        msgs = ded.message_ids.mapped('body')
        self.assertFalse(any('Modifications' in (m or '') for m in msgs))
    # ------------------------------------------------------------------
    # Cancel / reset
    # ------------------------------------------------------------------
    def test_cancel_draft(self):
        ded = self._make_deduction()
        ded.action_cancel()
        self.assertEqual(ded.state, 'cancelled')
        self.assertFalse(ded.approval_state)
    def test_cancel_active_skips_pending_lines(self):
        ded = self._make_deduction(amount=400.0, installments=4)
        ded.action_submit()
        # Mark first line as paid manually
        ded.line_ids[0].write({'state': 'paid'})
        ded.action_cancel()
        self.assertEqual(ded.state, 'cancelled')
        self.assertEqual(ded.line_ids[0].state, 'paid')
        self.assertTrue(all(l.state == 'skipped' for l in ded.line_ids[1:]))
    def test_cancel_completed_blocked(self):
        ded = self._make_deduction(amount=100.0, installments=1)
        ded.action_submit()
        ded.write({'state': 'completed'})
        with self.assertRaises(UserError):
            ded.action_cancel()
    def test_reset_to_draft_clears_lines_and_approvers(self):
        ded = self._make_deduction(self.type_loan,
                                   amount=1000.0, installments=4)
        self._walk_loan_to_pending_gm(ded)
        ded.action_gm_approve()
        self.assertEqual(ded.state, 'active')
        ded.action_reset_to_draft()
        self.assertEqual(ded.state, 'draft')
        self.assertFalse(ded.approval_state)
        self.assertFalse(ded.line_ids)
        self.assertFalse(ded.dm_approved_by)
        self.assertFalse(ded.hr_approved_by)
        self.assertFalse(ded.acc_approved_by)
        self.assertFalse(ded.gm_approved_by)
        self.assertEqual(ded.gm_original_amount, 0.0)
        self.assertEqual(ded.gm_original_installments, 0)
    def test_reset_blocked_when_paid_lines_exist(self):
        ded = self._make_deduction(amount=200.0, installments=2)
        ded.action_submit()
        ded.line_ids[0].write({'state': 'paid'})
        with self.assertRaises(UserError):
            ded.action_reset_to_draft()
    # ------------------------------------------------------------------
    # Unlink protection
    # ------------------------------------------------------------------
    def test_unlink_blocked_when_paid_lines_exist(self):
        ded = self._make_deduction(amount=200.0, installments=2)
        ded.action_submit()
        ded.line_ids[0].write({'state': 'paid'})
        with self.assertRaises(UserError):
            ded.unlink()
    def test_unlink_allowed_without_paid_lines(self):
        ded = self._make_deduction(amount=200.0, installments=2)
        ded.action_submit()
        line_ids = ded.line_ids.ids
        ded.unlink()
        self.assertFalse(self.env['ksw.deduction.line'].browse(line_ids).exists())
    # ------------------------------------------------------------------
    # Installment generation
    # ------------------------------------------------------------------
    def test_installment_residue_on_last_line(self):
        ded = self._make_deduction(amount=100.0, installments=3)
        ded.action_submit()
        amounts = ded.line_ids.mapped('amount')
        self.assertEqual(amounts[0], 33.33)
        self.assertEqual(amounts[1], 33.33)
        self.assertEqual(amounts[2], 33.34)
        self.assertEqual(round(sum(amounts), 2), 100.0)
    def test_installment_period_dates_monthly(self):
        ded = self._make_deduction(amount=1200.0, installments=12,
                                   start_month=date(2026, 1, 1))
        ded.action_submit()
        for i, line in enumerate(ded.line_ids, start=1):
            self.assertEqual(line.year, 2026)
            self.assertEqual(line.month, i)
            self.assertEqual(line.period_date, date(2026, i, 1))
    def test_lines_regenerated_when_already_present(self):
        ded = self._make_deduction(amount=100.0, installments=2)
        ded.action_submit()
        first_ids = set(ded.line_ids.ids)
        # Force regenerate
        ded._activate_and_generate_lines()
        new_ids = set(ded.line_ids.ids)
        self.assertEqual(len(new_ids), 2)
        self.assertFalse(first_ids & new_ids)
    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------
    def test_compute_progress(self):
        ded = self._make_deduction(amount=1000.0, installments=4)
        ded.action_submit()
        ded.line_ids[0].write({'state': 'paid'})
        ded.line_ids[1].write({'state': 'paid'})
        ded.line_ids[2].write({'state': 'skipped'})
        ded._compute_progress()  # ensure recomputation
        self.assertEqual(ded.total_paid, 500.0)
        self.assertEqual(ded.total_pending, 250.0)
        self.assertEqual(ded.progress_percent, 50.0)
    def test_progress_zero_amount(self):
        ded = self._make_deduction(amount=0.0, installments=1)
        # avoid action_submit (would raise) — just trigger compute
        ded._compute_progress()
        self.assertEqual(ded.progress_percent, 0.0)
    # ------------------------------------------------------------------
    # Type & line constraints
    # ------------------------------------------------------------------
    @mute_logger('odoo.sql_db')
    def test_unique_type_code(self):
        self.env['ksw.deduction.type'].create({
            'name': 'X', 'code': 'XYZ', 'category': 'borrowed',
        })
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['ksw.deduction.type'].create({
                    'name': 'Y', 'code': 'XYZ', 'category': 'borrowed',
                })
    @mute_logger('odoo.sql_db')
    def test_positive_default_installments_constraint(self):
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['ksw.deduction.type'].create({
                    'name': 'BadType', 'code': 'BAD',
                    'category': 'borrowed', 'default_installments': 0,
                })
    @mute_logger('odoo.sql_db')
    def test_line_month_range_constraint(self):
        ded = self._make_deduction(amount=100.0, installments=1)
        ded.action_submit()
        with self.assertRaises(IntegrityError):
            with self.cr.savepoint():
                self.env['ksw.deduction.line'].create({
                    'deduction_id': ded.id,
                    'year': 2026,
                    'month': 13,
                    'amount': 50.0,
                })
    def test_line_period_date_compute(self):
        ded = self._make_deduction(amount=100.0, installments=1,
                                   start_month=date(2026, 7, 1))
        ded.action_submit()
        line = ded.line_ids
        self.assertEqual(line.period_date, date(2026, 7, 1))
    def test_employee_ondelete_restrict(self):
        ded = self._make_deduction(amount=100.0, installments=1)
        ded.action_submit()
        with self.assertRaises(Exception):
            with mute_logger('odoo.sql_db'), self.cr.savepoint():
                self.employee.unlink()
    def test_type_ondelete_restrict(self):
        new_type = self.env['ksw.deduction.type'].create({
            'name': 'TmpType', 'code': 'TMPX', 'category': 'borrowed',
        })
        ded = self._make_deduction(ded_type=new_type, amount=100.0,
                                   installments=1)
        ded.action_submit()
        with self.assertRaises(Exception):
            with mute_logger('odoo.sql_db'), self.cr.savepoint():
                new_type.unlink()
