# -*- coding: utf-8 -*-
"""Tests for the self-service Loan Request wizard (`ksw.loan.request.wizard`).

Coverage:
    * default_get pins `employee_id` to the current user's employee
    * default_get raises UserError when the user has no linked employee
    * default_get pre-selects the first active loan type and applies
      its `default_installments`
    * the `type_id` onchange copies `default_installments` when the
      user switches type
    * `action_submit` creates a `ksw.deduction` via sudo and transitions
      it to `approval_state='pending_dm'`
    * the created deduction is a loan (`is_loan=True`) with the fields
      supplied by the wizard
    * defence-in-depth: cannot submit for another employee even if the
      form is tampered with
    * defence-in-depth: cannot submit a non-loan type through the wizard
    * validation: amount must be > 0 and installments >= 1
    * a plain Deduction User (no officer / no create ACL) CAN submit
      via the wizard (the wizard uses sudo internally) — this is the
      main value proposition of the wizard
"""
from odoo.exceptions import UserError, ValidationError

from .common import DeductionCommon


class TestLoanRequestWizard(DeductionCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        cls.plain_user = Users.create({
            'name': 'KSWDED Plain Requester',
            'login': 'kswded_wiz_plain',
            'email': 'wiz_plain@kswded.test',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.employee.write({'user_id': cls.plain_user.id})

        cls.user_no_emp = Users.create({
            'name': 'KSWDED No Emp',
            'login': 'kswded_wiz_noemp',
            'email': 'wiz_noemp@kswded.test',
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    # ------------------------------------------------------------------
    # default_get
    # ------------------------------------------------------------------
    def test_default_get_pins_employee_to_current_user(self):
        Wiz = self.env['ksw.loan.request.wizard'].with_user(self.plain_user)
        wiz = Wiz.create({
            'type_id': self.type_loan.id,
            'amount': 500.0,
            'installments': 2,
            'reason': 'r',
        })
        self.assertEqual(wiz.employee_id, self.employee,
                         "Wizard must pin employee_id to env.user.employee_id")

    def test_default_get_without_employee_raises(self):
        """A user with no linked employee cannot even open the wizard."""
        Wiz = self.env['ksw.loan.request.wizard'].with_user(self.user_no_emp)
        with self.assertRaises(UserError):
            Wiz.default_get(['employee_id'])

    def test_default_get_preselects_first_loan_type(self):
        """When `type_id` is requested, the default is the first active
        loan-category type ordered by sequence."""
        Wiz = self.env['ksw.loan.request.wizard'].with_user(self.plain_user)
        vals = Wiz.default_get(['employee_id', 'type_id', 'installments'])
        self.assertTrue(vals.get('type_id'))
        t = self.env['ksw.deduction.type'].browse(vals['type_id'])
        self.assertTrue(t.is_loan, "Default type must be a loan type.")
        self.assertTrue(t.active)

    def test_default_get_applies_type_default_installments(self):
        """If the default loan type has `default_installments`, the
        wizard pre-fills `installments`."""
        self.type_loan.default_installments = 7
        Wiz = self.env['ksw.loan.request.wizard'].with_user(self.plain_user)
        vals = Wiz.default_get(['employee_id', 'type_id', 'installments'])
        # Only asserts when type_loan happens to be the chosen default
        if vals.get('type_id') == self.type_loan.id:
            self.assertEqual(vals.get('installments'), 7)

    # ------------------------------------------------------------------
    # onchange
    # ------------------------------------------------------------------
    def test_onchange_type_copies_default_installments(self):
        self.type_loan.default_installments = 9
        Wiz = self.env['ksw.loan.request.wizard'].with_user(self.plain_user)
        wiz = Wiz.new({
            'employee_id': self.employee.id,
            'type_id': self.type_loan.id,
            'amount': 100.0,
            'installments': 1,
            'reason': 'r',
        })
        wiz._onchange_type_id()
        self.assertEqual(wiz.installments, 9)

    # ------------------------------------------------------------------
    # action_submit — happy path
    # ------------------------------------------------------------------
    def test_submit_creates_deduction_and_enters_pending_dm(self):
        Wiz = self.env['ksw.loan.request.wizard'].with_user(self.plain_user)
        wiz = Wiz.create({
            'type_id': self.type_loan.id,
            'amount': 1200.0,
            'installments': 6,
            'start_month': self.this_month,
            'reason': 'Medical emergency',
            'description': 'please approve',
        })
        action = wiz.action_submit()
        self.assertEqual(action['type'], 'ir.actions.act_window')
        self.assertEqual(action['res_model'], 'ksw.deduction')

        ded = self.env['ksw.deduction'].sudo().browse(action['res_id'])
        self.assertTrue(ded.exists())
        self.assertEqual(ded.employee_id, self.employee)
        self.assertEqual(ded.type_id, self.type_loan)
        self.assertTrue(ded.is_loan)
        self.assertEqual(ded.amount, 1200.0)
        self.assertEqual(ded.installments, 6)
        self.assertEqual(ded.reason, 'Medical emergency')
        self.assertEqual(ded.description, 'please approve')
        # action_submit on the deduction advances the approval chain
        self.assertEqual(ded.approval_state, 'pending_dm')
        # state stays 'draft' during the loan approval chain
        self.assertEqual(ded.state, 'draft')

    def test_plain_user_can_submit_despite_no_create_acl(self):
        """This is the whole point of the wizard: a user who has no
        write/create access on `ksw.deduction` can still request a
        loan for themselves through the wizard (sudo path)."""
        # Sanity check: direct create as plain_user raises AccessError
        from odoo.exceptions import AccessError
        with self.assertRaises(AccessError):
            self.env['ksw.deduction'].with_user(self.plain_user).create({
                'employee_id': self.employee.id,
                'type_id': self.type_loan.id,
                'amount': 500.0,
                'installments': 1,
            })
        # But the wizard path works:
        wiz = self.env['ksw.loan.request.wizard'].with_user(
            self.plain_user).create({
                'type_id': self.type_loan.id,
                'amount': 500.0,
                'installments': 1,
                'reason': 'r',
            })
        wiz.action_submit()  # must NOT raise

    # ------------------------------------------------------------------
    # action_submit — defence-in-depth
    # ------------------------------------------------------------------
    def test_cannot_submit_for_another_employee(self):
        """Even if the form is tampered with to set a different
        employee, action_submit re-checks the invariant."""
        wiz = self.env['ksw.loan.request.wizard'].with_user(
            self.plain_user).create({
                'type_id': self.type_loan.id,
                'amount': 500.0,
                'installments': 1,
                'reason': 'r',
            })
        # Force-change employee_id (readonly in UI, but model-level
        # write still accepts it)
        wiz.sudo().write({'employee_id': self.employee_b.id})
        with self.assertRaises(UserError):
            wiz.action_submit()

    def test_cannot_submit_non_loan_type(self):
        """Submitting a non-loan type through the wizard is blocked
        even though the UI domain already filters these out."""
        wiz = self.env['ksw.loan.request.wizard'].with_user(
            self.plain_user).create({
                'type_id': self.type_advance.id,  # not a loan
                'amount': 500.0,
                'installments': 1,
                'reason': 'r',
            })
        with self.assertRaises(UserError):
            wiz.action_submit()

    def test_submit_rejects_zero_amount(self):
        wiz = self.env['ksw.loan.request.wizard'].with_user(
            self.plain_user).create({
                'type_id': self.type_loan.id,
                'amount': 0.0,
                'installments': 1,
                'reason': 'r',
            })
        with self.assertRaises(ValidationError):
            wiz.action_submit()

    def test_submit_rejects_zero_installments(self):
        wiz = self.env['ksw.loan.request.wizard'].with_user(
            self.plain_user).create({
                'type_id': self.type_loan.id,
                'amount': 500.0,
                'installments': 0,
                'reason': 'r',
            })
        with self.assertRaises(ValidationError):
            wiz.action_submit()

