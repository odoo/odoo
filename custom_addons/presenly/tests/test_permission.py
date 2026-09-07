from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestPresenlyPermission(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        cls.employee_user = cls.env['res.users'].create({
            'name': 'Permission Employee',
            'login': 'permission_employee',
        })
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Permission Manager',
            'login': 'permission_manager',
            'group_ids': [(4, cls.env.ref(
                'presenly.group_presenly_approver'
            ).id)],
        })
        address = cls.env['res.partner'].create({
            'name': 'Permission School Address',
            'company_id': company.id,
            'partner_latitude': -6.2,
            'partner_longitude': 106.8,
        })
        cls.location = cls.env['hr.work.location'].create({
            'name': 'Permission School',
            'company_id': company.id,
            'address_id': address.id,
            'presenly_manager_id': cls.manager_user.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Permission Employee',
            'company_id': company.id,
            'user_id': cls.employee_user.id,
            'work_location_id': cls.location.id,
        })
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Permission Manager',
            'company_id': company.id,
            'user_id': cls.manager_user.id,
            'work_location_id': cls.location.id,
        })
        cls.employee.parent_id = cls.manager
        cls.permission_type = cls.env['presenly.permission.type'].create({
            'name': 'Late Arrival',
            'code': 'LATE_TEST',
            'company_id': company.id,
        })
        cls.env['presenly.approval.rule'].create({
            'name': 'Permission Manager',
            'company_id': company.id,
            'work_location_id': cls.location.id,
            'permission_type_id': cls.permission_type.id,
            'sequence': 10,
            'approver_type': 'employee_manager',
        })

    def _create_permission(self, request_date):
        return self.env['presenly.permission'].create({
            'employee_id': self.employee.id,
            'work_location_id': self.location.id,
            'permission_type_id': self.permission_type.id,
            'date_from': request_date,
            'date_to': request_date,
            'reason': 'Traffic',
        })

    def test_permission_type_opens_prefiltered_approval_route(self):
        self.assertEqual(self.permission_type.approval_route_count, 1)
        action = self.permission_type.action_open_approval_routes()
        self.assertEqual(
            action['domain'],
            [('permission_type_id', '=', self.permission_type.id)],
        )
        self.assertEqual(
            action['context']['default_permission_type_id'],
            self.permission_type.id,
        )
        self.assertFalse(action['context']['default_leave_type_id'])

    def test_permission_workflow(self):
        permission = self._create_permission('2030-02-01')
        permission.action_submit()
        self.assertEqual(permission.state, 'submitted')
        journey = permission.presenly_approval_request_id
        self.assertEqual(journey.state, 'pending')
        self.assertEqual(len(journey.step_ids), 1)
        self.assertEqual(permission.approval_progress_display, 'Level 1 of 1')

        permission.with_user(self.manager_user).action_approve()
        self.assertEqual(permission.state, 'approved')
        self.assertEqual(journey.state, 'approved')
        self.assertEqual(journey.step_ids.state, 'approved')
        self.assertEqual(permission.approval_progress_display, 'Completed (1/1)')

    def test_permission_chain_is_snapshotted(self):
        permission = self._create_permission('2030-02-05')
        permission.action_submit()
        journey = permission.presenly_approval_request_id
        self.employee.parent_id = False
        permission.with_user(self.manager_user).action_approve()
        self.assertEqual(permission.state, 'approved')
        self.assertEqual(journey.state, 'approved')

    def test_permission_cancel_closes_journey(self):
        permission = self._create_permission('2030-02-06')
        permission.action_submit()
        journey = permission.presenly_approval_request_id
        permission.action_cancel()
        self.assertEqual(permission.state, 'cancelled')
        self.assertEqual(journey.state, 'cancelled')

    def test_permission_rejection_reason(self):
        permission = self._create_permission('2030-02-02')
        permission.action_submit()
        with self.assertRaises(ValidationError):
            permission.with_user(self.manager_user).action_reject('')

    def test_permission_wrong_approver(self):
        permission = self._create_permission('2030-02-03')
        permission.action_submit()
        with self.assertRaises(UserError):
            permission.with_user(self.employee_user).action_approve()

    def test_unassigned_work_location_is_rejected_on_submit(self):
        other_address = self.env['res.partner'].create({
            'name': 'Unassigned School Address',
            'company_id': self.env.company.id,
            'partner_latitude': -6.3,
            'partner_longitude': 106.9,
        })
        other_location = self.env['hr.work.location'].create({
            'name': 'Unassigned School',
            'company_id': self.env.company.id,
            'address_id': other_address.id,
        })
        permission = self._create_permission('2030-02-04')
        permission.work_location_id = other_location
        with self.assertRaises(ValidationError):
            permission.action_submit()

    def test_delete_permission_policy(self):
        draft = self._create_permission('2030-02-10')
        approved = self._create_permission('2030-02-11')
        approved.action_submit()
        approved.with_user(self.manager_user).action_approve()

        hr_user = self.env['res.users'].create({
            'name': 'Permission HR',
            'login': 'permission_hr_delete',
            'group_ids': [(4, self.env.ref(
                'presenly.group_presenly_hr'
            ).id)],
        })
        # HR boleh menghapus draft/rejected/cancelled.
        draft.with_user(hr_user).unlink()
        self.assertFalse(draft.exists())
        # HR tidak boleh menghapus approved.
        with self.assertRaisesRegex(UserError, 'draft, rejected, or cancelled'):
            approved.with_user(hr_user).unlink()
        self.assertTrue(approved.exists())
        # Employee tidak boleh menghapus sama sekali.
        with self.assertRaisesRegex(UserError, 'Administrator or HR Officer'):
            self._create_permission('2030-02-12').with_user(
                self.employee_user
            ).unlink()
        # Journey ikut terhapus saat menghapus permission approved (dengan
        # konfirmasi), dan approval log tetap tersimpan sebagai audit trail.
        journey = approved.presenly_approval_request_id
        approved.action_delete_with_confirm()
        self.assertFalse(approved.exists())
        self.assertFalse(journey.exists())
        logs = self.env['presenly.approval.log'].search([
            ('request_model', '=', 'presenly.permission'),
            ('request_res_id', '=', approved.id),
        ])
        self.assertEqual(len(logs), 1)
