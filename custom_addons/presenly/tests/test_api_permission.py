from odoo import Command
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import JsonRpcException

@tagged('-at_install', 'post_install')
class TestPresenlyPermissionApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = 'presenly_permission_api_user'
        cls.password = 'presenly-permission-api-password'
        cls.user = new_test_user(
            cls.env,
            login=cls.login,
            password=cls.password,
            groups='base.group_user,presenly.group_presenly_employee',
        )
        cls.approver_login = 'presenly_permission_api_approver'
        cls.approver_password = 'presenly-permission-api-approver-password'
        cls.approver_user = new_test_user(
            cls.env,
            login=cls.approver_login,
            password=cls.approver_password,
            groups='base.group_user,presenly.group_presenly_approver',
        )
        cls.location_address = cls.env['res.partner'].create({
            'name': 'Permission API Location Address',
            'company_id': cls.env.company.id,
            'partner_latitude': -6.200000,
            'partner_longitude': 106.816666,
        })
        cls.location = cls.env['hr.work.location'].create({
            'name': 'Permission API Office',
            'company_id': cls.env.company.id,
            'address_id': cls.location_address.id,
        })
        cls.location_b = cls.env['hr.work.location'].create({
            'name': 'Permission API Office B',
            'company_id': cls.env.company.id,
            'address_id': cls.location_address.id,
        })
        cls.working_hours = cls.env['resource.calendar'].create({
            'name': 'Permission API Working Hours',
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
            'name': 'Permission API Employee',
            'user_id': cls.user.id,
            'company_id': cls.env.company.id,
            'work_location_id': cls.location.id,
            'resource_calendar_id': cls.working_hours.id,
            'tz': 'UTC',
        })
        cls.approver_employee = cls.env['hr.employee'].create({
            'name': 'Permission API Approver Employee',
            'user_id': cls.approver_user.id,
            'company_id': cls.env.company.id,
            'work_location_id': cls.location.id,
        })
        cls.permission_type = cls.env['presenly.permission.type'].create({
            'name': 'Permission API Errand',
            'code': 'PERM-API-ERRAND',
            'company_id': cls.env.company.id,
            'request_mode': 'both',
            'requires_attachment': False,
            'paid_status': 'paid',
        })
        cls.env['presenly.approval.rule'].create({
            'name': 'Permission API Approver',
            'company_id': cls.env.company.id,
            'permission_type_id': cls.permission_type.id,
            'sequence': 10,
            'approver_type': 'user',
            'approver_user_id': cls.approver_user.id,
        })

    def _create_permission(self, date='2030-05-10'):
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/permissions', {
                'permission_type_id': self.permission_type.id,
                'work_location_id': self.location.id,
                'request_mode': 'full_day',
                'date_from': date,
                'date_to': date,
                'reason': 'Emergency errand',
            },
        )
        self.assertTrue(created['success'])
        self.assertEqual(created['data']['state'], 'submitted')
        return created['data']['id']

    def test_permission_api_types(self):
        """permissions/types returns only active complete types for the company."""
        other = self.env['presenly.permission.type'].create({
            'name': 'Incomplete API Type',
            'code': False,
            'company_id': self.env.company.id,
        })
        inactive = self.env['presenly.permission.type'].create({
            'name': 'Inactive API Type',
            'code': 'PERM-API-INACTIVE',
            'company_id': self.env.company.id,
            'request_mode': 'both',
            'paid_status': 'policy',
            'active': False,
        })
        self.authenticate(self.login, self.password)
        result = self.make_jsonrpc_request('/api/presenly/v1/permissions/types')
        self.assertTrue(result['success'])
        types = result['data']
        self.assertTrue(any(
            item['id'] == self.permission_type.id for item in types
        ))
        self.assertTrue(any(
            item['code'] == 'PERM-API-ERRAND' for item in types
        ))
        self.assertFalse(any(item['id'] == other.id for item in types))
        self.assertFalse(any(item['id'] == inactive.id for item in types))

    def test_permission_api_full_approval_flow(self):
        self.authenticate(self.login, self.password)
        permission_id = self._create_permission()

        listed = self.make_jsonrpc_request('/api/presenly/v1/permissions/list')
        self.assertTrue(any(item['id'] == permission_id for item in listed['data']))

        # Approver sees it in queue and can approve.
        self.authenticate(self.approver_login, self.approver_password)
        queue = self.make_jsonrpc_request(
            '/api/presenly/v1/permissions/approval',
        )
        self.assertTrue(any(item['id'] == permission_id for item in queue['data']))

        approved = self.make_jsonrpc_request(
            f'/api/presenly/v1/permissions/{permission_id}/approve',
        )
        self.assertTrue(approved['success'])
        self.assertEqual(approved['data']['state'], 'approved')
        self.assertEqual(approved['data']['approval_progress'], 'Completed (1/1)')

        permission = self.env['presenly.permission'].sudo().browse(permission_id)
        self.assertEqual(permission.state, 'approved')
        self.assertEqual(
            permission.presenly_approval_request_id.state, 'approved',
        )

    def test_permission_api_reject_requires_reason(self):
        self.authenticate(self.login, self.password)
        permission_id = self._create_permission()

        self.authenticate(self.approver_login, self.approver_password)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                f'/api/presenly/v1/permissions/{permission_id}/reject', {},
            )

        rejected = self.make_jsonrpc_request(
            f'/api/presenly/v1/permissions/{permission_id}/reject', {
                'reason': 'Missing attachment',
            },
        )
        self.assertTrue(rejected['success'])
        self.assertEqual(rejected['data']['state'], 'rejected')
        self.assertEqual(rejected['data']['rejection_reason'], 'Missing attachment')

    def test_permission_api_can_approve_flags(self):
        self.authenticate(self.login, self.password)
        permission_id = self._create_permission()

        # Owner is not an approver; can cancel.
        owner_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/permissions/{permission_id}/can-approve',
        )
        self.assertTrue(owner_check['success'])
        self.assertFalse(owner_check['data']['can_approve'])
        self.assertFalse(owner_check['data']['can_reject'])
        self.assertTrue(owner_check['data']['can_cancel'])

        # Approver can approve/reject.
        self.authenticate(self.approver_login, self.approver_password)
        approver_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/permissions/{permission_id}/can-approve',
        )
        self.assertTrue(approver_check['success'])
        self.assertTrue(approver_check['data']['can_approve'])
        self.assertTrue(approver_check['data']['can_reject'])
        self.assertFalse(approver_check['data']['can_cancel'])

        # After approval, nothing left to approve/reject.
        self.make_jsonrpc_request(
            f'/api/presenly/v1/permissions/{permission_id}/approve',
        )
        after_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/permissions/{permission_id}/can-approve',
        )
        self.assertFalse(after_check['data']['can_approve'])
        self.assertFalse(after_check['data']['can_reject'])

    def test_permission_api_can_approve_batch(self):
        self.authenticate(self.login, self.password)
        first_id = self._create_permission('2030-06-01')
        second_id = self._create_permission('2030-06-02')

        self.authenticate(self.approver_login, self.approver_password)
        batch = self.make_jsonrpc_request(
            '/api/presenly/v1/permissions/can-approve/batch',
            {'ids': [first_id, second_id]},
        )
        self.assertTrue(batch['success'])
        self.assertEqual(len(batch['data']['items']), 2)
        for item in batch['data']['items']:
            self.assertTrue(item['can_approve'])
            self.assertTrue(item['can_reject'])
        self.assertEqual(batch['data']['unreadable_ids'], [])

    def test_permission_api_auto_location_unique(self):
        """No work_location_id: unique location for the period -> auto-filled."""
        self.authenticate(self.login, self.password)
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/permissions', {
                'permission_type_id': self.permission_type.id,
                'request_mode': 'full_day',
                'date_from': '2030-07-01',
                'date_to': '2030-07-01',
                'reason': 'Auto location unique',
            },
        )
        self.assertTrue(created['success'])
        self.assertEqual(created['data']['work_location_id'], self.location.id)

    def test_permission_api_auto_location_hours_overlap(self):
        """K2b: mode hours auto-resolves the location overlapping the hours."""
        self.env['presenly.work.location.schedule'].sudo().create([
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location.id,
                'schedule_type': 'date',
                'schedule_date': '2030-07-10',
                'hour_from': 8.0,
                'hour_to': 12.0,
            },
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location_b.id,
                'schedule_type': 'date',
                'schedule_date': '2030-07-10',
                'hour_from': 13.0,
                'hour_to': 17.0,
            },
        ])
        self.authenticate(self.login, self.password)
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/permissions', {
                'permission_type_id': self.permission_type.id,
                'request_mode': 'hours',
                'date_from': '2030-07-10',
                'date_to': '2030-07-10',
                'hour_from': 14.0,
                'hour_to': 16.0,
                'reason': 'Afternoon errand',
            },
        )
        self.assertTrue(created['success'])
        self.assertEqual(created['data']['work_location_id'], self.location_b.id)
        self.assertEqual(created['data']['request_mode'], 'hours')

    def test_permission_api_location_options_hours(self):
        """location-options for mode hours returns the overlapping location."""
        self.env['presenly.work.location.schedule'].sudo().create([
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location.id,
                'schedule_type': 'date',
                'schedule_date': '2030-07-20',
                'hour_from': 8.0,
                'hour_to': 12.0,
            },
            {
                'employee_id': self.employee.id,
                'work_location_id': self.location_b.id,
                'schedule_type': 'date',
                'schedule_date': '2030-07-20',
                'hour_from': 13.0,
                'hour_to': 17.0,
            },
        ])
        self.authenticate(self.login, self.password)
        result = self.make_jsonrpc_request(
            '/api/presenly/v1/permissions/location-options',
            {
                'date_from': '2030-07-20',
                'date_to': '2030-07-20',
                'request_mode': 'hours',
                'hour_from': 9.0,
                'hour_to': 10.0,
            },
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['data']['unique'])
        self.assertEqual(result['data']['location_id'], self.location.id)