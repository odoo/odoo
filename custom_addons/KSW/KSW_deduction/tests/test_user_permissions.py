# -*- coding: utf-8 -*-
"""Tests for per-user computed permission mirrors on `ksw.deduction`.

These computed booleans (`x_allow_edit_amount`, `x_allow_edit_installments`,
`x_allow_delete`) drive the form-view readonly expressions on Amount
and Installments. They must correctly mirror the user's Loan
Modification privilege level.

Also covers:
    * `x_can_dm_approve` — derived DM-approval authority
      (employee.parent_id.user_id OR Deduction Officer/Manager).
    * `x_can_submit` — Submit-button visibility logic.
"""
from .common import DeductionCommon


class TestUserPermissions(DeductionCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)

        def _mk(login, group_xmlids, employee=None):
            user = Users.create({
                'name': login,
                'login': login,
                'email': f'{login}@kswded.test',
                'group_ids': [(6, 0, [cls.env.ref(g).id
                                      for g in group_xmlids])],
            })
            if employee is not None:
                employee.write({'user_id': user.id})
            return user

        # Plain user (no Loan Modification privilege)
        cls.user_plain = _mk('kswded_perm_plain',
                             ['KSW_deduction.group_deduction_user'])
        # "Edit only"
        cls.user_edit = _mk('kswded_perm_edit',
                            ['KSW_deduction.group_deduction_user',
                             'KSW_deduction.group_loan_edit'])
        # "Delete only"
        cls.user_delete = _mk('kswded_perm_delete',
                              ['KSW_deduction.group_deduction_user',
                               'KSW_deduction.group_loan_delete'])
        # "Edit and Delete"
        cls.user_edit_delete = _mk('kswded_perm_ed',
                                   ['KSW_deduction.group_deduction_user',
                                    'KSW_deduction.group_loan_edit_delete'])
        # Deduction Manager — implies edit_delete
        cls.user_ded_mgr = _mk('kswded_perm_mgr',
                               ['KSW_deduction.group_deduction_manager'])

        # Users for DM-approve authority
        cls.line_mgr_user = _mk('kswded_perm_linemgr',
                                ['KSW_deduction.group_deduction_user'],
                                employee=cls.manager_emp)
        cls.officer_emp2 = cls.env['hr.employee'].create({
            'name': 'Perm Officer', 'department_id': cls.dept_b.id,
        })
        cls.user_officer = _mk('kswded_perm_officer',
                               ['KSW_deduction.group_deduction_officer'],
                               employee=cls.officer_emp2)
        cls.peer_user = _mk('kswded_perm_peer',
                            ['KSW_deduction.group_deduction_user'])

    # ------------------------------------------------------------------
    # x_allow_edit_* / x_allow_delete
    # ------------------------------------------------------------------
    def test_plain_user_has_no_loan_mod_perms(self):
        ded = self._make_deduction()
        rec = ded.with_user(self.user_plain)
        self.assertFalse(rec.x_allow_edit_amount)
        self.assertFalse(rec.x_allow_edit_installments)
        self.assertFalse(rec.x_allow_delete)

    def test_edit_only_grants_edit_not_delete(self):
        ded = self._make_deduction()
        rec = ded.with_user(self.user_edit)
        self.assertTrue(rec.x_allow_edit_amount)
        self.assertTrue(rec.x_allow_edit_installments)
        self.assertFalse(rec.x_allow_delete)

    def test_delete_only_grants_delete_not_edit(self):
        ded = self._make_deduction()
        rec = ded.with_user(self.user_delete)
        self.assertFalse(rec.x_allow_edit_amount)
        self.assertFalse(rec.x_allow_edit_installments)
        self.assertTrue(rec.x_allow_delete)

    def test_edit_and_delete_grants_all(self):
        ded = self._make_deduction()
        rec = ded.with_user(self.user_edit_delete)
        self.assertTrue(rec.x_allow_edit_amount)
        self.assertTrue(rec.x_allow_edit_installments)
        self.assertTrue(rec.x_allow_delete)

    def test_deduction_manager_does_not_inherit_loan_mod(self):
        """Deduction Management and Loan Modification are orthogonal
        privileges. A Deduction Manager without an explicit Loan
        Modification grant must NOT get edit/delete on loan amount /
        installments — that privilege is per-user and explicit."""
        ded = self._make_deduction()
        rec = ded.with_user(self.user_ded_mgr)
        self.assertFalse(rec.x_allow_edit_amount)
        self.assertFalse(rec.x_allow_edit_installments)
        self.assertFalse(rec.x_allow_delete)

    # ------------------------------------------------------------------
    # x_can_dm_approve
    # ------------------------------------------------------------------
    def test_line_manager_can_dm_approve_own_report(self):
        ded = self._make_deduction(self.type_loan)
        ded.action_submit()  # → pending_dm
        rec = ded.with_user(self.line_mgr_user)
        self.assertTrue(
            rec.x_can_dm_approve,
            "employee.parent_id.user_id must be allowed to DM-approve.",
        )

    def test_officer_can_dm_approve_any_record(self):
        ded = self._make_deduction(self.type_loan)
        ded.action_submit()
        rec = ded.with_user(self.user_officer)
        self.assertTrue(rec.x_can_dm_approve)

    def test_peer_user_cannot_dm_approve(self):
        ded = self._make_deduction(self.type_loan)
        ded.action_submit()
        rec = ded.with_user(self.peer_user)
        self.assertFalse(rec.x_can_dm_approve)

    def test_dm_approve_action_blocked_for_unauthorized(self):
        """The action itself re-checks x_can_dm_approve and raises."""
        from odoo.exceptions import UserError
        ded = self._make_deduction(self.type_loan)
        ded.action_submit()
        with self.assertRaises(UserError):
            ded.with_user(self.peer_user).action_dm_approve()

    # ------------------------------------------------------------------
    # x_can_submit
    # ------------------------------------------------------------------
    def test_officer_can_submit_any_draft(self):
        """Officers can submit on behalf of anyone (covers employees
        without a user account)."""
        ded = self._make_deduction()
        rec = ded.with_user(self.user_officer)
        self.assertTrue(rec.x_can_submit)

    def test_peer_cannot_submit_somebody_elses_draft(self):
        ded = self._make_deduction()  # created by admin
        rec = ded.with_user(self.peer_user)
        self.assertFalse(rec.x_can_submit)


