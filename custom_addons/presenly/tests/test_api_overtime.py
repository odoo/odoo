from odoo import Command
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import JsonRpcException


@tagged('-at_install', 'post_install')
class TestPresenlyOvertimeApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = 'presenly_overtime_api_user'
        cls.password = 'presenly-overtime-api-password'
        cls.user = new_test_user(
            cls.env,
            login=cls.login,
            password=cls.password,
            groups='base.group_user,presenly.group_presenly_employee',
        )
        cls.approver_login = 'presenly_overtime_api_approver'
        cls.approver_password = 'presenly-overtime-api-approver-password'
        cls.approver_user = new_test_user(
            cls.env,
            login=cls.approver_login,
            password=cls.approver_password,
            groups='base.group_user,presenly.group_presenly_approver',
        )
        cls.location_address = cls.env['res.partner'].create({
            'name': 'Overtime API Location Address',
            'company_id': cls.env.company.id,
            'partner_latitude': -6.200000,
            'partner_longitude': 106.816666,
        })
        cls.location = cls.env['hr.work.location'].create({
            'name': 'Overtime API Office',
            'company_id': cls.env.company.id,
            'address_id': cls.location_address.id,
        })
        cls.working_hours = cls.env['resource.calendar'].create({
            'name': 'Overtime API Working Hours',
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
            'name': 'Overtime API Employee',
            'user_id': cls.user.id,
            'company_id': cls.env.company.id,
            'work_location_id': cls.location.id,
            'resource_calendar_id': cls.working_hours.id,
            'tz': 'UTC',
        })
        cls.approver_employee = cls.env['hr.employee'].create({
            'name': 'Overtime API Approver Employee',
            'user_id': cls.approver_user.id,
            'company_id': cls.env.company.id,
            'work_location_id': cls.location.id,
            'resource_calendar_id': cls.working_hours.id,
            'tz': 'UTC',
        })
        # Attendance evidence for the employee on the overtime test days (proof).
        # hr.attendance.create is intentionally blocked; use the server entry point.
        for day in ('2030-08-01', '2030-08-02', '2030-08-03', '2030-08-04',
                    '2030-08-05', '2030-08-06'):
            cls.env['hr.attendance']._presenly_mobile_create({
                'employee_id': cls.employee.id,
                'check_in': f'{day} 08:00:00',
                'check_out': f'{day} 17:00:00',
            })
        cls.env['presenly.approval.rule'].sudo().create({
            'name': 'Overtime API Approver',
            'company_id': cls.env.company.id,
            'is_overtime_route': True,
            'sequence': 10,
            'approver_type': 'user',
            'approver_user_id': cls.approver_user.id,
        })

    def _create_overtime(self, date='2030-08-01',
                         hour_from=18.0, hour_to=22.0):
        payload = {
            'date': date,
            'hour_from': hour_from,
            'hour_to': hour_to,
            'reason': 'Server maintenance',
        }
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/overtime/requests', payload,
        )
        self.assertTrue(created['success'])
        self.assertEqual(created['data']['state'], 'submitted')
        return created['data']

    def test_overtime_api_full_approval_flow(self):
        self.authenticate(self.login, self.password)
        data = self._create_overtime()
        overtime_id = data['id']
        # Duration computed server-side (18:00->22:00 = 4h).
        self.assertEqual(data['duration_hours'], 4.0)
        self.assertTrue(data['has_attendance_evidence'])
        self.assertEqual(data['work_location_id'], self.location.id)
        self.assertEqual(data['hour_from'], 18.0)
        self.assertEqual(data['hour_to'], 22.0)
        self.assertEqual(data['date'], '2030-08-01')
        self.assertEqual(data['reason'], 'Server maintenance')

        listed = self.make_jsonrpc_request('/api/presenly/v1/overtime/requests/list')
        self.assertTrue(any(item['id'] == overtime_id for item in listed['data']))

        # Approver sees it in queue.
        self.authenticate(self.approver_login, self.approver_password)
        queue = self.make_jsonrpc_request('/api/presenly/v1/overtime/requests/approval')
        self.assertTrue(any(item['id'] == overtime_id for item in queue['data']))

        approved = self.make_jsonrpc_request(
            f'/api/presenly/v1/overtime/requests/{overtime_id}/approve',
        )
        self.assertTrue(approved['success'])
        self.assertEqual(approved['data']['state'], 'approved')
        self.assertEqual(approved['data']['approval_progress'], 'Completed (1/1)')

        record = self.env['presenly.overtime.request'].sudo().browse(overtime_id)
        self.assertEqual(record.state, 'approved')
        self.assertEqual(
            record.presenly_approval_request_id.state, 'approved',
        )

    def test_overtime_api_reject_requires_reason(self):
        self.authenticate(self.login, self.password)
        overtime_id = self._create_overtime()['id']

        self.authenticate(self.approver_login, self.approver_password)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                f'/api/presenly/v1/overtime/requests/{overtime_id}/reject', {},
            )

        rejected = self.make_jsonrpc_request(
            f'/api/presenly/v1/overtime/requests/{overtime_id}/reject', {
                'reason': 'Not approved by policy',
            },
        )
        self.assertTrue(rejected['success'])
        self.assertEqual(rejected['data']['state'], 'rejected')
        self.assertEqual(
            rejected['data']['rejection_reason'], 'Not approved by policy',
        )

    def test_overtime_api_one_per_day_constraint(self):
        self.authenticate(self.login, self.password)
        self._create_overtime('2030-08-02')
        with self.assertRaises(JsonRpcException):
            self._create_overtime('2030-08-02')

    def test_overtime_api_requires_attendance_evidence(self):
        self.authenticate(self.login, self.password)
        with self.assertRaises(JsonRpcException):
            self._create_overtime('2030-09-02')  # no attendance that day

    def test_overtime_api_can_approve_flags(self):
        self.authenticate(self.login, self.password)
        overtime_id = self._create_overtime('2030-08-03')['id']

        # Owner is not an approver; can cancel.
        owner_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/overtime/requests/{overtime_id}/can-approve',
        )
        self.assertTrue(owner_check['success'])
        self.assertFalse(owner_check['data']['can_approve'])
        self.assertFalse(owner_check['data']['can_reject'])
        self.assertTrue(owner_check['data']['can_cancel'])

        # Approver can approve/reject.
        self.authenticate(self.approver_login, self.approver_password)
        approver_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/overtime/requests/{overtime_id}/can-approve',
        )
        self.assertTrue(approver_check['success'])
        self.assertTrue(approver_check['data']['can_approve'])
        self.assertTrue(approver_check['data']['can_reject'])

    def test_overtime_api_can_approve_batch(self):
        self.authenticate(self.login, self.password)
        first = self._create_overtime('2030-08-04')['id']
        second = self._create_overtime('2030-08-05')['id']

        self.authenticate(self.approver_login, self.approver_password)
        batch = self.make_jsonrpc_request(
            '/api/presenly/v1/overtime/requests/can-approve/batch',
            {'ids': [first, second]},
        )
        self.assertTrue(batch['success'])
        self.assertEqual(len(batch['data']['items']), 2)
        for item in batch['data']['items']:
            self.assertTrue(item['can_approve'])
            self.assertTrue(item['can_reject'])
        self.assertEqual(batch['data']['unreadable_ids'], [])

    def test_overtime_api_accepts_midnight_hour(self):
        """Midnight (00:00) is a valid 24h hour, not a missing value."""
        self.authenticate(self.login, self.password)
        created = self.make_jsonrpc_request(
            '/api/presenly/v1/overtime/requests', {
                'date': '2030-08-01',
                'hour_from': 0.0,
                'hour_to': 4.0,
                'reason': 'Night maintenance',
            },
        )
        self.assertTrue(created['success'])
        self.assertEqual(created['data']['hour_from'], 0.0)
        self.assertEqual(created['data']['hour_to'], 4.0)
        self.assertEqual(created['data']['duration_hours'], 4.0)

    def test_overtime_api_cancel_by_owner(self):
        """Owner can cancel a submitted overtime request."""
        self.authenticate(self.login, self.password)
        overtime_id = self._create_overtime('2030-08-06')['id']

        # Approver cannot cancel (cancellation follows owner/manager rights).
        self.authenticate(self.approver_login, self.approver_password)
        approver_check = self.make_jsonrpc_request(
            f'/api/presenly/v1/overtime/requests/{overtime_id}/can-approve',
        )
        self.assertFalse(approver_check['data']['can_cancel'])

        # Owner cancels via the API.
        self.authenticate(self.login, self.password)
        cancelled = self.make_jsonrpc_request(
            f'/api/presenly/v1/overtime/requests/{overtime_id}/cancel',
        )
        self.assertTrue(cancelled['success'])
        self.assertEqual(cancelled['data']['state'], 'cancelled')

        record = self.env['presenly.overtime.request'].sudo().browse(overtime_id)
        self.assertEqual(record.state, 'cancelled')
        self.assertEqual(
            record.presenly_approval_request_id.state, 'cancelled',
        )

    def test_overtime_api_cannot_cancel_after_approval(self):
        """A final (non-cancellable) request rejects cancel with an error."""
        self.authenticate(self.login, self.password)
        overtime_id = self._create_overtime('2030-08-03')['id']

        self.authenticate(self.approver_login, self.approver_password)
        approved = self.make_jsonrpc_request(
            f'/api/presenly/v1/overtime/requests/{overtime_id}/approve',
        )
        self.assertTrue(approved['success'])
        self.assertEqual(approved['data']['state'], 'approved')

        # Approver is not the owner, so cancel is rejected.
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                f'/api/presenly/v1/overtime/requests/{overtime_id}/cancel',
            )

    def test_overtime_api_location_options(self):
        """location-options returns the unique recommended location for a day."""
        self.authenticate(self.login, self.password)
        result = self.make_jsonrpc_request(
            '/api/presenly/v1/overtime/requests/location-options',
            {'date': '2030-08-01'},
        )
        self.assertTrue(result['success'])
        self.assertTrue(result['data']['unique'])
        self.assertEqual(result['data']['location_id'], self.location.id)
        self.assertEqual(result['data']['locations'], [{
            'id': self.location.id, 'name': self.location.name,
        }])