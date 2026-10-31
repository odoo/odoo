from odoo import Command
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import JsonRpcException

@tagged('-at_install', 'post_install')
class TestPresenlyLeaveApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = 'presenly_leave_api_user'
        cls.password = 'presenly-leave-api-password'
        cls.user = new_test_user(
            cls.env,
            login=cls.login,
            password=cls.password,
            groups='base.group_user,presenly.group_presenly_employee',
        )
        cls.approver_login = 'presenly_leave_api_approver'
        cls.approver_password = 'presenly-leave-api-approver-password'
        cls.approver_user = new_test_user(
            cls.env,
            login=cls.approver_login,
            password=cls.approver_password,
            groups='base.group_user,presenly.group_presenly_approver',
        )
        cls.location_address = cls.env['res.partner'].create({
            'name': 'Leave API Location Address',
            'company_id': cls.env.company.id,
            'partner_latitude': -6.200000,
            'partner_longitude': 106.816666,
        })
        cls.location = cls.env['hr.work.location'].create({
            'name': 'Leave API Office',
            'company_id': cls.env.company.id,
            'address_id': cls.location_address.id,
        })
        cls.location_b = cls.env['hr.work.location'].create({
            'name': 'Leave API Office B',
            'company_id': cls.env.company.id,
            'address_id': cls.location_address.id,
        })
        cls.working_hours = cls.env['resource.calendar'].create({
            'name': 'Leave API Working Hours',
            'company_id': cls.env.company.id,
            'tz': 'UTC',
            'attendance_ids': [
                Command.create({
                    'name': f'Day {idx}',
                    'dayofweek': str(idx),
                    'day_period': 'morning',
                    'hour_from': 8.0,
                    'hour_to': 17.0,
                })
                for idx in range(7)
            ],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Leave API Employee',
            'user_id': cls.user.id,
            'company_id': cls.env.company.id,
            'work_location_id': cls.location.id,
            'resource_calendar_id': cls.working_hours.id,
            'tz': 'UTC',
        })
        cls.approver_employee = cls.env['hr.employee'].create({
            'name': 'Leave API Approver Employee',
            'user_id': cls.approver_user.id,
            'company_id': cls.env.company.id,
            'work_location_id': cls.location.id,
        })
        cls.leave_type = cls.env['hr.leave.type'].create({
            'name': 'Leave API Annual Leave',
            'company_id': cls.env.company.id,
            'requires_allocation': False,
            'leave_validation_type': 'manager',
        })
        cls.env['presenly.approval.rule'].create({
            'name': 'Leave API Approver',
            'company_id': cls.env.company.id,
            'leave_type_id': cls.leave_type.id,
            'sequence': 10,
            'approver_type': 'user',
            'approver_user_id': cls.approver_user.id,
        })

    def test_leave_api_full_approval_flow(self):
        self.authenticate(self.login, self.password)

        types = self.make_jsonrpc_request(
            '/api/presenly/v1/leave/types',
        )
        self.assertTrue(types['success'])
        type_ids = [t['id'] for t in types['data']]
        self.assertIn(self.leave_type.id, type_ids)

        created = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves', {
                'leave_type_id': self.leave_type.id,
                'work_location_id': self.location.id,
                'date_from': '2030-01-21',
                'date_to': '2030-01-21',
                'reason': 'Family event',
            },
        )
        self.assertTrue(created['success'])
        leave_id = created['data']['id']
        self.assertEqual(created['data']['approval_state'], 'pending')
        self.assertEqual(created['data']['leave_type_id'], self.leave_type.id)

        listed = self.make_jsonrpc_request('/api/presenly/v1/leaves/list')
        self.assertTrue(any(item['id'] == leave_id for item in listed['data']))

        # Re-authenticate as the approver.
        self.authenticate(self.approver_login, self.approver_password)
        queue = self.make_jsonrpc_request('/api/presenly/v1/leaves/approval')
        self.assertTrue(
            any(item['id'] == leave_id for item in queue['data'])
        )

        approved = self.make_jsonrpc_request(
            f'/api/presenly/v1/leaves/{leave_id}/approve',
        )
        self.assertTrue(approved['success'])
        self.assertEqual(approved['data']['approval_state'], 'approved')
        self.assertEqual(approved['data']['state'], 'validate')

        leave = self.env['hr.leave'].sudo().browse(leave_id)
        self.assertEqual(leave.state, 'validate')
        self.assertEqual(leave.presenly_approval_state, 'approved')
        self.assertEqual(
            leave.presenly_approval_request_id.state, 'approved',
        )

    def test_leave_api_reject_requires_reason(self):
        self.authenticate(self.login, self.password)
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves', {
                'leave_type_id': self.leave_type.id,
                'work_location_id': self.location.id,
                'date_from': '2030-02-01',
                'date_to': '2030-02-01',
                'reason': 'Appointment',
            },
        )
        leave_id = created['data']['id']

        self.authenticate(self.approver_login, self.approver_password)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                f'/api/presenly/v1/leaves/{leave_id}/reject', {},
            )

        rejected = self.make_jsonrpc_request(
            f'/api/presenly/v1/leaves/{leave_id}/reject', {
                'reason': 'Needs rescheduling',
            },
        )
        self.assertTrue(rejected['success'])
        self.assertEqual(rejected['data']['approval_state'], 'rejected')
        self.assertEqual(rejected['data']['state'], 'refuse')

    def test_leave_api_can_approve_flags(self):
        # Employee submits a request.
        self.authenticate(self.login, self.password)
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves', {
                'leave_type_id': self.leave_type.id,
                'work_location_id': self.location.id,
                'date_from': '2030-03-01',
                'date_to': '2030-03-01',
                'reason': 'Capability check',
            },
        )
        leave_id = created['data']['id']

        # Owner employee is NOT an approver at the active level.
        owner_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/leaves/{leave_id}/can-approve',
        )
        self.assertTrue(owner_check['success'])
        self.assertFalse(owner_check['data']['can_approve'])
        self.assertFalse(owner_check['data']['can_reject'])
        self.assertTrue(owner_check['data']['can_cancel'])

        # Approver IS an approver at the active level.
        self.authenticate(self.approver_login, self.approver_password)
        approver_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/leaves/{leave_id}/can-approve',
        )
        self.assertTrue(approver_check['success'])
        self.assertTrue(approver_check['data']['can_approve'])
        self.assertTrue(approver_check['data']['can_reject'])

        # After approval, the leave is no longer actionable by the approver.
        approved = self.make_jsonrpc_request(
            f'/api/presenly/v1/leaves/{leave_id}/approve',
        )
        self.assertTrue(approved['success'])
        after_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/leaves/{leave_id}/can-approve',
        )
        self.assertFalse(after_check['data']['can_approve'])
        self.assertFalse(after_check['data']['can_reject'])

    def test_leave_api_can_approve_batch(self):
        self.authenticate(self.login, self.password)
        first = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves', {
                'leave_type_id': self.leave_type.id,
                'work_location_id': self.location.id,
                'date_from': '2030-04-01',
                'date_to': '2030-04-01',
                'reason': 'Batch one',
            },
        )
        second = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves', {
                'leave_type_id': self.leave_type.id,
                'work_location_id': self.location.id,
                'date_from': '2030-04-02',
                'date_to': '2030-04-02',
                'reason': 'Batch two',
            },
        )
        first_id = first['data']['id']
        second_id = second['data']['id']

        self.authenticate(self.approver_login, self.approver_password)
        batch = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves/can-approve/batch',
            {'ids': [first_id, second_id]},
        )
        self.assertTrue(batch['success'])
        self.assertEqual(len(batch['data']['items']), 2)
        for item in batch['data']['items']:
            self.assertTrue(item['can_approve'])
            self.assertTrue(item['can_reject'])
        self.assertEqual(batch['data']['unreadable_ids'], [])

    def test_leave_api_auto_location_unique(self):
        """No work_location_id: unique location for the period -> auto-filled."""
        self.authenticate(self.login, self.password)
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves', {
                'leave_type_id': self.leave_type.id,
                'date_from': '2030-05-01',
                'date_to': '2030-05-01',
                'reason': 'Auto location unique',
            },
        )
        self.assertTrue(created['success'])
        self.assertEqual(created['data']['work_location_id'], self.location.id)

    def test_leave_api_location_options(self):
        """location-options returns unique/by_date for a single-location period."""
        self.authenticate(self.login, self.password)
        result = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves/location-options',
            {'date_from': '2030-05-10', 'date_to': '2030-05-10'},
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['data']['unique'])
        self.assertEqual(result['data']['location_id'], self.location.id)
        self.assertEqual(
            result['data']['by_date']['2030-05-10']['id'],
            self.location.id,
        )

    def test_leave_api_location_options_ambiguous_two_dates(self):
        """Two days, different locations -> unique=false + per-date map."""
        self.env['presenly.work.location.schedule'].sudo().create([
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location.id,
                'schedule_type': 'date',
                'schedule_date': '2030-06-10',
                'hour_from': 8.0,
                'hour_to': 12.0,
            },
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location_b.id,
                'schedule_type': 'date',
                'schedule_date': '2030-06-11',
                'hour_from': 8.0,
                'hour_to': 12.0,
            },
        ])
        self.authenticate(self.login, self.password)
        result = self.make_jsonrpc_request(
            '/api/presenly/v1/leaves/location-options',
            {'date_from': '2030-06-10', 'date_to': '2030-06-11'},
        )
        self.assertTrue(result['success'])
        self.assertFalse(result['data']['unique'])
        self.assertFalse(result['data']['location_id'])
        self.assertEqual(result['data']['by_date']['2030-06-10']['id'], self.location.id)
        self.assertEqual(result['data']['by_date']['2030-06-11']['id'], self.location_b.id)

    def test_leave_api_create_rejects_multi_location_period(self):
        """Two days with different locations -> create without location rejected (K1)."""
        self.env['presenly.work.location.schedule'].sudo().create([
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location.id,
                'schedule_type': 'date',
                'schedule_date': '2030-06-20',
                'hour_from': 8.0,
                'hour_to': 12.0,
            },
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location_b.id,
                'schedule_type': 'date',
                'schedule_date': '2030-06-21',
                'hour_from': 8.0,
                'hour_to': 12.0,
            },
        ])
        self.authenticate(self.login, self.password)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                '/api/presenly/v1/leaves', {
                    'leave_type_id': self.leave_type.id,
                    'date_from': '2030-06-20',
                    'date_to': '2030-06-21',
                    'reason': 'Multi location',
                },
            )