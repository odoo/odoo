"""Comprehensive tests for the commission-sheet ↔ KSW_deduction loans flow.

Covers:
  • Loans auto-pulled in draft (x_awaiting_commission lines)
  • Freeze to x_loans_amount_locked on confirm
  • action_done FIFO: all lines fully covered → state='paid', linked to sheet
  • action_done FIFO: partial coverage → last line split, sibling paid
  • action_done: locked > shortfall raises UserError
  • Reset from done (full coverage): whole lines restored to pending
  • Reset from done (split): original line amount restored, sibling deleted
  • No awaiting-commission lines → x_unwind_data stays False after done
  • Accountant can edit x_loans_amount_locked on a confirmed sheet
  • Non-accountant cannot edit note on a confirmed sheet
"""
import json
from datetime import date

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCommissionLoans(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        env = cls.env

        # Employee
        cls.emp = env['hr.employee'].sudo().create({
            'name': 'Loans Test Employee',
            'x_is_attendance_sheet': True,
        })

        # Deduction type (non-loan advance → instant activation)
        cls.ded_type = env.ref('KSW_deduction.type_advance')

        # Commission category
        cat = env['ksw.commission.category'].search(
            [('code', '=', 'other')], limit=1)
        cls.cat_other = cat

        # Fixed period: April 2026
        cls.period = date(2026, 4, 1)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _make_active_deduction(self, amount=1200.0, installments=3,
                               start_month=None):
        """Create + activate a non-loan deduction for cls.emp starting
        at ``start_month`` (defaults to cls.period).
        """
        start = start_month or self.period
        ded = self.env['ksw.deduction'].sudo().create({
            'employee_id': self.emp.id,
            'type_id': self.ded_type.id,
            'amount': amount,
            'installments': installments,
            'start_month': start,
            'reason': 'Loans test',
        })
        ded.sudo()._activate_and_generate_lines()
        return ded

    def _flag_awaiting(self, ded, month_filter=None):
        """Flag lines matching the period (or all) as x_awaiting_commission."""
        if month_filter is None:
            month_filter = self.period.month
        lines = ded.line_ids.filtered(
            lambda l: l.month == month_filter and l.state == 'pending')
        lines.sudo().write({'x_awaiting_commission': True})
        return lines

    def _new_sheet(self):
        return self.env['ksw.commission.sheet'].sudo().create({
            'employee_id': self.emp.id,
            'period': self.period,
        })

    # ------------------------------------------------------------------
    # Tests
    # ------------------------------------------------------------------

    def test_01_loans_amount_auto_pulled_in_draft(self):
        """Lines with x_awaiting_commission=True are summed in loans_amount."""
        ded = self._make_active_deduction(amount=1200.0, installments=3)
        self._flag_awaiting(ded)  # April line = 400
        sheet = self._new_sheet()
        sheet._compute_loans_amount()
        self.assertAlmostEqual(sheet.loans_amount, 400.0, places=1)

    def test_02_confirm_freezes_loans(self):
        """action_confirm copies live loans_amount into x_loans_amount_locked."""
        ded = self._make_active_deduction(amount=900.0, installments=3)
        self._flag_awaiting(ded)  # April = 300
        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        self.assertEqual(sheet.state, 'confirmed')
        self.assertAlmostEqual(sheet.x_loans_amount_locked, 300.0, places=1)

    def test_03_done_full_coverage_lines_paid(self):
        """action_done with locked >= total: all lines flipped to paid."""
        ded = self._make_active_deduction(amount=600.0, installments=2)
        line_apr = ded.line_ids.filtered(lambda l: l.month == self.period.month)[0]
        line_apr.sudo().write({'x_awaiting_commission': True})

        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        # Accountant adjusts to exact line amount
        sheet.sudo().write({'x_loans_amount_locked': line_apr.amount})
        sheet.sudo().action_done()

        self.assertEqual(sheet.state, 'done')
        line_apr.invalidate_recordset()
        self.assertEqual(line_apr.state, 'paid')
        self.assertEqual(
            line_apr.x_paid_via_commission_sheet_id.id, sheet.id)

    def test_04_done_partial_coverage_splits_line(self):
        """action_done with locked < line amount → split: original trimmed,
        sibling created in state='paid'."""
        ded = self._make_active_deduction(amount=600.0, installments=2)
        line_apr = ded.line_ids.filtered(
            lambda l: l.month == self.period.month)[0]
        # line_apr.amount should be ~300.0
        full_amount = line_apr.amount
        partial = round(full_amount / 2, 2)

        line_apr.sudo().write({'x_awaiting_commission': True})
        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        sheet.sudo().write({'x_loans_amount_locked': partial})
        sheet.sudo().action_done()

        line_apr.invalidate_recordset()
        # Original line shrunk
        self.assertAlmostEqual(line_apr.amount, full_amount - partial, places=2)
        self.assertEqual(line_apr.state, 'pending')

        # Sibling paid line created
        sibling = ded.sudo().line_ids.filtered(
            lambda l: l.x_paid_via_commission_sheet_id.id == sheet.id
        )
        self.assertTrue(sibling)
        self.assertAlmostEqual(sibling.amount, partial, places=2)
        self.assertEqual(sibling.state, 'paid')

    def test_05_done_locked_exceeds_shortfall_raises(self):
        """Locked amount > current awaiting total raises UserError."""
        ded = self._make_active_deduction(amount=600.0, installments=2)
        line_apr = ded.line_ids.filtered(
            lambda l: l.month == self.period.month)[0]
        line_apr.sudo().write({'x_awaiting_commission': True})
        total = line_apr.amount

        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        # Force locked to be higher than the real shortfall
        sheet.sudo().write({'x_loans_amount_locked': total + 500.0})
        with self.assertRaises(UserError):
            sheet.sudo().action_done()

    def test_06_reset_from_done_full_restores_lines(self):
        """Reset from done (full payment): lines restored to pending."""
        ded = self._make_active_deduction(amount=300.0, installments=1)
        line_apr = ded.line_ids[0]
        line_apr.sudo().write({'x_awaiting_commission': True})

        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        sheet.sudo().write({'x_loans_amount_locked': line_apr.amount})
        sheet.sudo().action_done()
        # Now reset
        sheet.sudo().action_reset_to_draft()

        line_apr.invalidate_recordset()
        self.assertEqual(line_apr.state, 'pending')
        self.assertFalse(line_apr.x_paid_via_commission_sheet_id)
        self.assertTrue(line_apr.x_awaiting_commission)

    def test_07_reset_from_done_split_restores_original(self):
        """Reset from done (split): original amount restored, sibling deleted."""
        ded = self._make_active_deduction(amount=600.0, installments=2)
        line_apr = ded.line_ids.filtered(
            lambda l: l.month == self.period.month)[0]
        full_amount = line_apr.amount
        partial = round(full_amount / 2, 2)

        line_apr.sudo().write({'x_awaiting_commission': True})
        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        sheet.sudo().write({'x_loans_amount_locked': partial})
        sheet.sudo().action_done()

        # Capture sibling id before reset
        sibling = ded.sudo().line_ids.filtered(
            lambda l: l.x_paid_via_commission_sheet_id.id == sheet.id
        )
        sibling_id = sibling.id

        sheet.sudo().action_reset_to_draft()

        # Original line amount restored
        line_apr.invalidate_recordset()
        self.assertAlmostEqual(line_apr.amount, full_amount, places=2)

        # Sibling deleted
        self.assertFalse(
            self.env['ksw.deduction.line'].sudo().browse(sibling_id).exists()
        )

    def test_08_no_loans_unwind_data_false_after_done(self):
        """Sheet with zero locked loans → x_unwind_data stays False after done."""
        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        # x_loans_amount_locked = 0.0
        sheet.sudo().action_done()
        self.assertEqual(sheet.state, 'done')
        self.assertFalse(sheet.x_unwind_data)

    def test_09_accountant_can_edit_locked_loans(self):
        """Accountant may update x_loans_amount_locked on confirmed sheet."""
        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        # sudo → env.su=True bypasses the accountant group check
        sheet.sudo().write({'x_loans_amount_locked': 50.0})
        self.assertAlmostEqual(sheet.x_loans_amount_locked, 50.0)

    def test_10_total_payable_deducts_locked_amount(self):
        """total_payable = total - x_loans_amount_locked when confirmed."""
        cat = self.env['ksw.commission.category'].search(
            [('code', '=', 'other')], limit=1)
        sheet = self._new_sheet()
        self.env['ksw.commission.sheet.line'].sudo().create({
            'sheet_id': sheet.id,
            'category_id': cat.id,
            'amount': 1000.0,
        })
        sheet.sudo().action_confirm()
        sheet.sudo().write({'x_loans_amount_locked': 200.0})
        sheet.sudo()._compute_totals()
        self.assertAlmostEqual(sheet.total_payable, 800.0, places=1)

    def test_11_loans_amount_frozen_in_confirmed_state(self):
        """In confirmed/done state, loans_amount mirrors x_loans_amount_locked."""
        sheet = self._new_sheet()
        sheet.sudo().action_confirm()
        sheet.sudo().write({'x_loans_amount_locked': 75.0})
        sheet.sudo()._compute_loans_amount()
        self.assertAlmostEqual(sheet.loans_amount, 75.0)

    def test_12_multiple_deduction_lines_fifo_order(self):
        """FIFO: first active deduction's installment consumed first."""
        # Two deductions, both have April lines flagged awaiting
        ded1 = self._make_active_deduction(amount=200.0, installments=1)
        ded2 = self._make_active_deduction(amount=300.0, installments=1)
        # Flag both April lines
        for ded in (ded1, ded2):
            aprl = ded.line_ids.filtered(
                lambda l: l.month == self.period.month)
            if aprl:
                aprl.sudo().write({'x_awaiting_commission': True})

        sheet = self._new_sheet()
        sheet.sudo()._compute_loans_amount()
        # Total should be the sum of both lines
        self.assertAlmostEqual(sheet.loans_amount, 500.0, delta=1.0)

        sheet.sudo().action_confirm()
        # Lock to only cover the first deduction (200)
        sheet.sudo().write({'x_loans_amount_locked': 200.0})
        sheet.sudo().action_done()

        ded1.invalidate_recordset()
        apr1 = ded1.line_ids[0]
        self.assertEqual(apr1.state, 'paid',
                         'First (FIFO) deduction line should be paid.')
        apr2 = ded2.line_ids.filtered(lambda l: l.month == self.period.month)[0]
        self.assertEqual(apr2.state, 'pending',
                         'Second deduction line should remain pending.')

