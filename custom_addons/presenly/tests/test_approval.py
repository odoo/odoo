from lxml import etree

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestPresenlyLeaveApproval(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.employee_user = cls.env['res.users'].create({
            'name': 'Leave Employee',
            'login': 'presenly_leave_employee',
            'email': 'presenly.employee@example.com',
        })
        cls.manager_user = cls.env['res.users'].create({
            'name': 'Leave Manager',
            'login': 'presenly_leave_manager',
            'email': 'presenly.manager@example.com',
            'group_ids': [(4, cls.env.ref(
                'presenly.group_presenly_approver'
            ).id)],
        })
        cls.location_address = cls.env['res.partner'].create({
            'name': 'Approval School Address',
            'company_id': cls.company.id,
            'partner_latitude': -6.2,
            'partner_longitude': 106.8,
        })
        cls.location = cls.env['hr.work.location'].create({
            'name': 'Approval School',
            'company_id': cls.company.id,
            'address_id': cls.location_address.id,
            'presenly_manager_id': cls.manager_user.id,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Leave Employee',
            'company_id': cls.company.id,
            'user_id': cls.employee_user.id,
            'work_location_id': cls.location.id,
        })
        cls.manager = cls.env['hr.employee'].create({
            'name': 'Leave Manager',
            'company_id': cls.company.id,
            'user_id': cls.manager_user.id,
            'work_location_id': cls.location.id,
        })
        cls.employee.parent_id = cls.manager
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Presenly Annual Leave',
            'company_id': cls.company.id,
            'requires_allocation': False,
            'leave_validation_type': 'manager',
        })
        cls.rule_one = cls.env['presenly.approval.rule'].create({
            'name': 'Employee Manager Level',
            'company_id': cls.company.id,
            'work_location_id': cls.location.id,
            'leave_type_id': cls.leave_type.id,
            'sequence': 10,
            'approver_type': 'employee_manager',
        })
        cls.rule_two = cls.env['presenly.approval.rule'].create({
            'name': 'Location Manager Level',
            'company_id': cls.company.id,
            'work_location_id': cls.location.id,
            'leave_type_id': cls.leave_type.id,
            'sequence': 20,
            # Database selection key retained for upgrade compatibility.
            'approver_type': 'unit_manager',
        })

    def _create_leave(self):
        return self.env['hr.leave'].with_user(self.employee_user).create({
            'employee_id': self.employee.id,
            'holiday_status_id': self.leave_type.id,
            'presenly_work_location_id': self.location.id,
            'request_date_from': '2030-01-10',
            'request_date_to': '2030-01-10',
            'name': 'Test leave',
        })

    def test_two_level_approval(self):
        leave = self._create_leave()
        self.assertEqual(leave.state, 'confirm')
        self.assertEqual(leave.presenly_approval_state, 'not_started')
        self.assertEqual(leave.holiday_status_id.leave_validation_type, 'hr')

        leave.action_presenly_submit()
        self.assertEqual(leave.presenly_approval_state, 'pending')
        self.assertEqual(leave.presenly_approval_level, 0)
        journey = leave.presenly_approval_request_id
        self.assertEqual(journey.state, 'pending')
        self.assertEqual(len(journey.step_ids), 2)
        self.assertEqual(journey.current_step_id.level, 1)

        leave.with_user(self.manager_user).action_presenly_approve()
        self.assertEqual(leave.presenly_approval_level, 1)
        self.assertEqual(leave.presenly_approval_state, 'pending')
        self.assertEqual(journey.current_step_id.level, 2)
        self.assertEqual(journey.step_ids[0].state, 'approved')

        leave.with_user(self.manager_user).action_presenly_approve()
        self.assertEqual(leave.presenly_approval_state, 'approved')
        self.assertEqual(leave.state, 'validate')
        self.assertEqual(journey.state, 'approved')
        self.assertFalse(journey.current_step_id)
        self.assertEqual(self.env['presenly.approval.log'].search_count([
            ('request_model', '=', 'hr.leave'),
            ('request_res_id', '=', leave.id),
        ]), 2)

    def test_approval_route_navigation_and_connected_ui(self):
        self.assertEqual(self.leave_type.presenly_approval_route_count, 2)
        leave_action = self.leave_type.action_open_presenly_approval_routes()
        self.assertEqual(leave_action['domain'], [('leave_type_id', '=', self.leave_type.id)])
        self.assertEqual(
            leave_action['context']['default_leave_type_id'], self.leave_type.id,
        )
        self.assertFalse(leave_action['context']['default_permission_type_id'])

        self.assertEqual(self.location.presenly_approval_override_count, 2)
        location_action = self.location.action_open_presenly_approval_overrides()
        self.assertEqual(
            location_action['domain'], [('work_location_id', '=', self.location.id)],
        )
        self.assertEqual(
            location_action['context']['default_work_location_id'], self.location.id,
        )

        route_form = self.env['presenly.approval.rule'].get_view(
            view_id=self.env.ref('presenly.view_presenly_approval_rule_form').id,
            view_type='form',
        )
        route_root = etree.fromstring(route_form['arch'].encode())
        self.assertEqual(len(route_root.xpath("//group[@string='1. Request Type']")), 1)
        self.assertEqual(
            len(route_root.xpath("//group[@string='2. Work Location Scope']")), 1,
        )
        self.assertEqual(len(route_root.xpath("//group[@string='3. Who Approves']")), 1)

        leave_type_form = self.env['hr.leave.type'].get_view(
            view_id=self.env.ref('hr_holidays.edit_holiday_status_form').id,
            view_type='form',
        )
        leave_root = etree.fromstring(leave_type_form['arch'].encode())
        self.assertEqual(
            len(leave_root.xpath(
                "//button[@name='action_open_presenly_approval_routes']"
            )),
            1,
        )

    def test_native_approval_cannot_bypass_presenly(self):
        leave = self._create_leave()
        with self.assertRaises(UserError):
            leave.with_user(self.manager_user).action_approve()
        with self.assertRaises(UserError):
            leave.with_user(self.manager_user)._action_validate(check_state=False)
        self.assertNotEqual(leave.state, 'validate')

    def test_native_approval_flags_are_forced_false_for_presenly(self):
        leave = self._create_leave()
        leave.action_presenly_submit()
        leave.invalidate_recordset([
            'can_approve', 'can_validate', 'can_refuse', 'can_back_to_approve',
        ])
        self.assertFalse(leave.can_approve)
        self.assertFalse(leave.can_validate)
        self.assertFalse(leave.can_refuse)
        self.assertFalse(leave.can_back_to_approve)
        manager_leave = leave.with_user(self.manager_user)
        self.assertTrue(manager_leave.presenly_can_approve)

    def test_approval_chain_is_snapshotted_at_submission(self):
        leave = self._create_leave()
        leave.action_presenly_submit()
        journey = leave.presenly_approval_request_id
        assigned_users = journey.step_ids.mapped('assigned_user_ids')
        self.assertIn(self.manager_user, assigned_users)

        self.employee.parent_id = False
        self.location.presenly_manager_id = False
        self.rule_one.active = False
        self.rule_two.active = False

        # The submitted request keeps its original levels and approvers.
        self.assertEqual(len(journey.step_ids), 2)
        leave.with_user(self.manager_user).action_presenly_approve()
        leave.with_user(self.manager_user).action_presenly_approve()
        self.assertEqual(leave.state, 'validate')

    def test_pending_leave_cancel_closes_journey(self):
        leave = self._create_leave()
        leave.action_presenly_submit()
        journey = leave.presenly_approval_request_id
        leave.action_presenly_cancel()
        self.assertEqual(leave.state, 'cancel')
        self.assertEqual(leave.presenly_approval_state, 'cancelled')
        self.assertEqual(journey.state, 'cancelled')
        self.assertFalse(journey.current_step_id)

    def test_rejection_requires_reason(self):
        leave = self._create_leave()
        leave.action_presenly_submit()
        with self.assertRaises(ValidationError):
            leave.with_user(self.manager_user).action_presenly_reject('')

    def test_wrong_approver_is_rejected(self):
        leave = self._create_leave()
        leave.action_presenly_submit()
        with self.assertRaises(UserError):
            leave.with_user(self.employee_user).action_presenly_approve()
