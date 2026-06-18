# -*- coding: utf-8 -*-
"""Tests for ACLs, record rules, and group implication chain."""
from odoo.exceptions import AccessError
from odoo.tools import mute_logger
from .common import DeductionCommon
class TestDeductionSecurity(DeductionCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Users = cls.env['res.users'].with_context(no_reset_password=True)
        def _mk(login, group_xmlid, employee=None):
            user = Users.create({
                'name': login,
                'login': login,
                'email': f'{login}@kswded.test',
                'group_ids': [(6, 0, [cls.env.ref(group_xmlid).id])],
            })
            if employee is not None:
                employee.write({'user_id': user.id})
            return user
        cls.user_dept_user = _mk('kswded_user',
                                 'KSW_deduction.group_deduction_user',
                                 employee=cls.employee)
        # Officer in Dept B (so we can verify they still see Dept A)
        cls.officer_emp = cls.env['hr.employee'].create({
            'name': 'Officer Emp', 'department_id': cls.dept_b.id,
        })
        cls.user_officer = _mk('kswded_officer',
                               'KSW_deduction.group_deduction_officer',
                               employee=cls.officer_emp)
        cls.manager_emp_for_user = cls.env['hr.employee'].create({
            'name': 'Mgr Emp', 'department_id': cls.dept_a.id,
        })
        cls.user_manager = _mk('kswded_manager',
                               'KSW_deduction.group_deduction_manager',
                               employee=cls.manager_emp_for_user)
        # DM Approver has no dedicated group anymore — DM authority is
        # derived from being the employee's parent_id.user_id. Create a
        # user and attach it to the employee's manager record.
        cls.user_dm = _mk('kswded_dm',
                          'KSW_deduction.group_deduction_user',
                          employee=cls.manager_emp)
        cls.user_hr = _mk('kswded_hr', 'KSW_deduction.group_loan_hr')
        cls.user_acc = _mk('kswded_acc', 'KSW_deduction.group_loan_acc')
        cls.user_gm = _mk('kswded_gm', 'KSW_deduction.group_loan_gm')
    # ------------------------------------------------------------------
    # Type ACL
    # ------------------------------------------------------------------
    def test_type_read_by_any_internal_user(self):
        # base.group_user has read on the type
        plain = self.env['res.users'].create({
            'name': 'plain', 'login': 'kswded_plain',
            'email': 'plain@kswded.test',
            'group_ids': [(6, 0, [self.env.ref('base.group_user').id])],
        })
        self.type_loan.with_user(plain).read(['name'])  # no error
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_type_write_blocked_for_user(self):
        with self.assertRaises(AccessError):
            self.type_loan.with_user(self.user_dept_user).write({'name': 'X'})
    def test_type_full_access_for_manager(self):
        new_type = self.env['ksw.deduction.type'].with_user(
            self.user_manager).create({
                'name': 'MgrType', 'code': 'MGRX', 'category': 'borrowed',
            })
        new_type.write({'name': 'MgrType2'})
        new_type.unlink()
    # ------------------------------------------------------------------
    # Deduction CRUD per group
    # ------------------------------------------------------------------
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_user_cannot_create_or_unlink(self):
        with self.assertRaises(AccessError):
            self.env['ksw.deduction'].with_user(self.user_dept_user).create({
                'employee_id': self.employee.id,
                'type_id': self.type_advance.id,
                'amount': 100.0, 'installments': 1,
            })
    def test_officer_can_create(self):
        ded = self.env['ksw.deduction'].with_user(self.user_officer).create({
            'employee_id': self.employee.id,
            'type_id': self.type_advance.id,
            'amount': 100.0, 'installments': 1,
        })
        ded.with_user(self.user_officer).write({'reason': 'test'})
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_officer_cannot_unlink(self):
        ded = self._make_deduction()
        with self.assertRaises(AccessError):
            ded.with_user(self.user_officer).unlink()
    def test_manager_can_unlink(self):
        ded = self._make_deduction()
        ded.with_user(self.user_manager).unlink()
    @mute_logger('odoo.addons.base.models.ir_model')
    def test_loan_approver_cannot_create(self):
        for u in (self.user_dm, self.user_hr, self.user_acc, self.user_gm):
            with self.assertRaises(AccessError):
                self.env['ksw.deduction'].with_user(u).create({
                    'employee_id': self.employee.id,
                    'type_id': self.type_loan.id,
                    'amount': 100.0, 'installments': 1,
                })
    def test_dm_can_approve(self):
        ded = self._make_deduction(self.type_loan)
        ded.action_submit()
        ded.with_user(self.user_dm).action_dm_approve()
        self.assertEqual(ded.approval_state, 'pending_hr')
    # ------------------------------------------------------------------
    # Record rules
    # ------------------------------------------------------------------
    def test_user_sees_own_and_subordinates(self):
        """A plain Deduction User sees their OWN deductions + the
        deductions of any employee who reports directly to them.
        Department membership is NOT used."""
        # Make employee_b (Dept B) a direct report of self.employee
        # whose user is user_dept_user.
        self.employee_b.write({'parent_id': self.employee.id})
        own = self._make_deduction(employee=self.employee)
        sub = self._make_deduction(employee=self.employee_b)
        # Peer in the same dept but NOT a subordinate — must be hidden.
        peer_emp = self.env['hr.employee'].create({
            'name': 'Peer in Dept A', 'department_id': self.dept_a.id,
        })
        peer = self._make_deduction(employee=peer_emp)
        Ded = self.env['ksw.deduction'].with_user(self.user_dept_user)
        visible = Ded.search([('id', 'in', (own + sub + peer).ids)])
        self.assertIn(own, visible)
        self.assertIn(sub, visible, "Subordinate's deduction must be visible.")
        self.assertNotIn(
            peer, visible,
            "Same-department non-subordinate must NOT be visible.")
        with self.assertRaises(AccessError):
            peer.with_user(self.user_dept_user).read(['name'])
    def test_officer_sees_all_departments(self):
        own = self._make_deduction(employee=self.employee)
        other = self._make_deduction(employee=self.employee_b)
        Ded = self.env['ksw.deduction'].with_user(self.user_officer)
        visible = Ded.search([('id', 'in', (own + other).ids)])
        self.assertIn(own, visible)
        self.assertIn(other, visible)
    def test_user_without_employee_sees_nothing(self):
        u = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'no_emp', 'login': 'kswded_noemp',
            'email': 'noemp@kswded.test',
            'group_ids': [(6, 0,
                           [self.env.ref(
                               'KSW_deduction.group_deduction_user').id])],
        })
        own = self._make_deduction(employee=self.employee)
        visible = self.env['ksw.deduction'].with_user(u).search([
            ('id', '=', own.id)])
        self.assertFalse(visible)
    # ------------------------------------------------------------------
    # Group hierarchy
    # ------------------------------------------------------------------
    def test_group_implication_chain(self):
        g_user = self.env.ref('KSW_deduction.group_deduction_user')
        g_off = self.env.ref('KSW_deduction.group_deduction_officer')
        g_mgr = self.env.ref('KSW_deduction.group_deduction_manager')
        # Officer implies user
        self.assertIn(g_user, g_off.implied_ids | g_off.all_implied_ids)
        # Manager implies officer (and transitively user)
        self.assertIn(g_off, g_mgr.implied_ids | g_mgr.all_implied_ids)
    def test_privileges_assigned(self):
        cat = self.env.ref('KSW_deduction.module_category_ksw_deduction')
        priv_mgmt = self.env.ref('KSW_deduction.privilege_deduction_management')
        priv_loan = self.env.ref('KSW_deduction.privilege_loan_approval')
        self.assertEqual(priv_mgmt.category_id, cat)
        self.assertEqual(priv_loan.category_id, cat)
        self.assertEqual(self.env.ref(
            'KSW_deduction.group_deduction_user').privilege_id, priv_mgmt)
        # DM Approver group no longer exists; HR is the first explicit
        # loan-approval group.
        self.assertEqual(self.env.ref(
            'KSW_deduction.group_loan_hr').privilege_id, priv_loan)

    def test_base_user_implies_deduction_user(self):
        """Every internal user is automatically a Deduction User
        (this removes the 'No' option from the privilege dropdown)."""
        base_user = self.env.ref('base.group_user')
        ded_user = self.env.ref('KSW_deduction.group_deduction_user')
        self.assertIn(
            ded_user,
            base_user.implied_ids | base_user.all_implied_ids,
            "base.group_user must imply group_deduction_user so that "
            "every internal user has at least Deduction 'User' rights.",
        )

    def test_no_dm_approver_group(self):
        """The old 'DM Approver' group must not exist — DM authority
        is derived from employee.parent_id.user_id."""
        g = self.env.ref(
            'KSW_deduction.group_loan_dm', raise_if_not_found=False)
        self.assertFalse(g, "group_loan_dm must be removed.")
