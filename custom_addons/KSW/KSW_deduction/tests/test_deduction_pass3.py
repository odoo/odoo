# -*- coding: utf-8 -*-
"""Tests for Pass 3 — workflow confirmations, accountant snapshot,
monthly totals, and submit-button visibility."""
from odoo.exceptions import ValidationError

from .common import DeductionCommon


class TestDeductionPass3(DeductionCommon):
    """HR / Accountant approval gates + monthly totals + submit visibility."""

    # ==================================================================
    # HR confirmation gate
    # ==================================================================
    def test_hr_approve_blocked_without_confirmation(self):
        """HR approval raises ValidationError if checkbox isn't ticked."""
        ded = self._make_deduction(self.type_loan, amount=1000, installments=2)
        ded.action_submit()
        ded.action_dm_approve()
        # Not ticking the checkbox:
        with self.assertRaises(ValidationError):
            ded.action_hr_approve()
        # Ticking allows approval:
        ded.x_hr_no_penalties_confirmed = True
        ded.action_hr_approve()
        self.assertEqual(ded.approval_state, 'pending_acc')

    # ==================================================================
    # Accountant confirmation gate + snapshot + modification log
    # ==================================================================
    def test_acc_approve_blocked_without_confirmation(self):
        """Accounting approval raises ValidationError if checkbox isn't ticked."""
        ded = self._make_deduction(self.type_loan, amount=1000, installments=2)
        ded.action_submit()
        ded.action_dm_approve()
        ded.x_hr_no_penalties_confirmed = True
        ded.action_hr_approve()
        with self.assertRaises(ValidationError):
            ded.action_acc_approve()
        ded.x_acc_budget_confirmed = True
        ded.action_acc_approve()
        self.assertEqual(ded.approval_state, 'pending_gm')

    def test_acc_snapshot_captured_on_entry(self):
        """Entering pending_acc snapshots amount & installments."""
        ded = self._make_deduction(self.type_loan, amount=1500, installments=6)
        ded.action_submit()
        ded.action_dm_approve()
        ded.x_hr_no_penalties_confirmed = True
        ded.action_hr_approve()  # → pending_acc
        self.assertEqual(ded.acc_original_amount, 1500.0)
        self.assertEqual(ded.acc_original_installments, 6)

    def test_acc_modification_logged_in_chatter(self):
        """Installment change by accountant is logged in chatter."""
        ded = self._make_deduction(self.type_loan, amount=1500, installments=6)
        ded.action_submit()
        ded.action_dm_approve()
        ded.x_hr_no_penalties_confirmed = True
        ded.action_hr_approve()
        # Accountant changes installments
        ded.installments = 10
        ded.x_acc_budget_confirmed = True
        ded.action_acc_approve()
        msgs = ded.message_ids.mapped('body')
        self.assertTrue(
            any('Installments: 6 → 10' in m for m in msgs),
            'Accountant modification should be logged in chatter',
        )

    # ==================================================================
    # Reset to draft clears confirmations
    # ==================================================================
    def test_reset_to_draft_clears_confirmations(self):
        ded = self._make_deduction(self.type_loan, amount=1000, installments=2)
        ded.action_submit()
        ded.action_dm_approve()
        ded.x_hr_no_penalties_confirmed = True
        ded.action_hr_approve()
        ded.x_acc_budget_confirmed = True
        ded.action_acc_approve()
        ded.action_cancel()
        ded.action_reset_to_draft()
        self.assertFalse(ded.x_hr_no_penalties_confirmed)
        self.assertFalse(ded.x_acc_budget_confirmed)
        self.assertEqual(ded.acc_original_amount, 0.0)
        self.assertEqual(ded.acc_original_installments, 0)

    # ==================================================================
    # x_can_submit visibility
    # ==================================================================
    def test_x_can_submit_true_for_creator(self):
        """A record's creator always sees the Submit button (draft state)."""
        ded = self._make_deduction()
        # self.env.uid == create_uid → can submit
        self.assertTrue(ded.x_can_submit)

    def test_x_can_submit_false_for_non_creator_non_officer(self):
        """A plain internal user who didn't create the record and isn't
        an officer cannot see the Submit button."""
        plain_user = self.env['res.users'].create({
            'name': 'KSWDED Plain Pass3',
            'login': 'kswded_plain_pass3',
            'email': 'plain_pass3@kswded.test',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        ded = self._make_deduction()
        self.assertFalse(ded.with_user(plain_user).x_can_submit)

    # ==================================================================
    # Monthly total related field
    # ==================================================================
    def test_x_emp_monthly_total_related(self):
        """x_emp_monthly_total mirrors employee's current-month total."""
        # Create an active deduction with current-month line
        ded = self._make_deduction(amount=500, installments=1,
                                   start_month=self.this_month)
        ded.action_submit()
        self.assertEqual(ded.state, 'active')
        self.assertAlmostEqual(
            ded.x_emp_monthly_total,
            self.employee.x_deduction_monthly_total,
            places=2,
        )
        # The employee's total should include at least this deduction's line
        self.assertGreaterEqual(self.employee.x_deduction_monthly_total, 500.0)

    # ==================================================================
    # action_create_new_penalty
    # ==================================================================
    def test_action_create_new_penalty_returns_act_window(self):
        """Button returns an action defaulting employee_id."""
        ded = self._make_deduction()
        action = ded.action_create_new_penalty()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'ksw.deduction')
        self.assertEqual(
            action['context'].get('default_employee_id'),
            self.employee.id,
        )
        # Defaults to internal penalty type if defined
        self.assertEqual(
            action['context'].get('default_type_id'),
            self.type_internal_pen.id,
        )

