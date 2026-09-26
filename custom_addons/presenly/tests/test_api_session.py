import base64
import hashlib
import io

from PIL import Image

from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tests.common import JsonRpcException


@tagged('-at_install', 'post_install')
class TestPresenlyApiSession(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.login = 'presenly_api_session_user'
        cls.password = 'presenly-api-session-password'
        cls.user = new_test_user(
            cls.env,
            login=cls.login,
            password=cls.password,
            groups='base.group_user,presenly.group_presenly_employee',
        )
        cls.location_address = cls.env['res.partner'].create({
            'name': 'Presenly API Geofence Address',
            'company_id': cls.env.company.id,
            'partner_latitude': -6.200000,
            'partner_longitude': 106.816666,
        })
        cls.location = cls.env['hr.work.location'].create({
            'name': 'Presenly API Office',
            'company_id': cls.env.company.id,
            'address_id': cls.location_address.id,
            'presenly_radius_meters': 150.0,
            'presenly_gps_accuracy_limit_meters': 50.0,
            'presenly_require_selfie_check_in': True,
            'presenly_require_selfie_check_out': True,
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'Presenly API Session Employee',
            'user_id': cls.user.id,
            'company_id': cls.env.company.id,
            'work_location_id': cls.location.id,
        })
        image = io.BytesIO()
        Image.new('RGB', (8, 8), (32, 64, 96)).save(image, format='JPEG')
        cls.selfie = base64.b64encode(image.getvalue()).decode('ascii')

    def test_attendance_status_requires_valid_session(self):
        route = '/api/presenly/v1/attendance/status'

        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(route)

        self.authenticate(self.login, self.password)
        result = self.make_jsonrpc_request(route)
        self.assertTrue(result['success'])
        self.assertEqual(result['data']['employee_id'], self.employee.id)
        self.assertEqual(result['data']['state'], 'checked_out')
        self.assertTrue(result['data']['can_check_in'])
        self.assertFalse(result['data']['can_check_out'])
        self.assertEqual(
            result['data']['available_work_locations'][0]['id'],
            self.location.id,
        )
        self.assertIn('recommended_work_location_id', result['data'])
        self.assertIn('auto_selection_supported', result['data'])
        self.assertIn('ambiguous', result['data'])
        self.assertEqual(result['data']['recommended_work_location_id'], self.location.id)
        self.assertTrue(result['data']['auto_selection_supported'])
        self.assertFalse(result['data']['ambiguous'])
        self.assertNotIn('approved_leave', result['data'])
        self.assertNotIn('approved_permission', result['data'])
        self.assertFalse(result['error'])

        response = self.url_open('/web/session/destroy', json={})
        response.raise_for_status()
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(route)

    def test_employee_can_check_in_and_out_with_validated_selfies(self):
        self.authenticate(self.login, self.password)
        payload = {
            'work_location_id': self.location.id,
            'latitude': -6.200000,
            'longitude': 106.816666,
            'accuracy': 8.5,
            'selfie': self.selfie,
            'device_id': 'mobile-device-test-001',
        }

        checked_in = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/check-in', payload,
        )
        self.assertTrue(checked_in['success'])
        self.assertEqual(checked_in['data']['state'], 'checked_in')
        self.assertEqual(
            checked_in['data']['work_location_id'], self.location.id,
        )
        self.assertTrue(checked_in['data']['validation']['geofence_valid'])
        self.assertTrue(checked_in['data']['validation']['selfie_received'])

        attendance_id = checked_in['data']['attendance_id']
        status = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/status',
        )
        self.assertEqual(status['data']['state'], 'checked_in')
        self.assertEqual(status['data']['attendance_id'], attendance_id)
        self.assertFalse(status['data']['can_check_in'])
        self.assertTrue(status['data']['can_check_out'])

        checked_out = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/check-out', payload,
        )
        self.assertTrue(checked_out['success'])
        self.assertEqual(checked_out['data']['state'], 'checked_out')
        self.assertEqual(checked_out['data']['attendance_id'], attendance_id)
        self.assertTrue(checked_out['data']['check_out'])
        self.assertTrue(checked_out['data']['validation']['same_work_location'])
        self.assertTrue(checked_out['data']['validation']['selfie_received'])

        attendance = self.env['hr.attendance'].sudo().browse(attendance_id)
        attendance.invalidate_recordset()
        self.assertTrue(attendance.exists())
        self.assertEqual(attendance.employee_id, self.employee)
        self.assertEqual(attendance.presenly_source, 'mobile')
        self.assertEqual(attendance.color, 10)
        self.assertTrue(attendance.presenly_selfie_in_attachment_id)
        self.assertTrue(attendance.presenly_selfie_out_attachment_id)
        self.assertFalse(attendance.presenly_selfie_in_attachment_id.public)
        self.assertFalse(attendance.presenly_selfie_out_attachment_id.public)

        events = self.env['presenly.attendance.event'].sudo().search([
            ('attendance_id', '=', attendance.id),
        ], order='event_time asc')
        self.assertEqual(len(events), 2)
        self.assertEqual(set(events.mapped('event_type')), {'check_in', 'check_out'})
        self.assertEqual(set(events.mapped('validation_status')), {'success'})
        self.assertEqual(
            set(events.mapped('device_id_hash')),
            {hashlib.sha256(b'mobile-device-test-001').hexdigest()},
        )

        final_status = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/status',
        )
        self.assertEqual(final_status['data']['state'], 'checked_out')
        self.assertFalse(final_status['data']['attendance_id'])

    def test_native_kiosk_barcode_manual_and_systray_are_disabled(self):
        attendance_count = self.env['hr.attendance'].sudo().search_count([
            ('employee_id', '=', self.employee.id),
        ])
        token = self.env.company.attendance_kiosk_key

        kiosk_response = self.url_open(self.env.company.attendance_kiosk_url)
        self.assertEqual(kiosk_response.status_code, 404)

        barcode_result = self.make_jsonrpc_request(
            '/hr_attendance/attendance_barcode_scanned', {
                'token': token,
                'barcode': 'PRESENLY-DISABLED-BADGE',
                'latitude': -6.200000,
                'longitude': 106.816666,
            },
        )
        self.assertEqual(barcode_result, {})

        manual_result = self.make_jsonrpc_request(
            '/hr_attendance/manual_selection', {
                'token': token,
                'employee_id': self.employee.id,
                'pin_code': False,
                'latitude': -6.200000,
                'longitude': 106.816666,
            },
        )
        self.assertEqual(manual_result, {})

        self.authenticate(self.login, self.password)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                '/hr_attendance/systray_check_in_out', {
                    'latitude': -6.200000,
                    'longitude': 106.816666,
                },
            )
        systray_data = self.make_jsonrpc_request(
            '/hr_attendance/attendance_user_data',
        )
        self.assertFalse(systray_data['display_systray'])

        self.env.invalidate_all()
        self.assertEqual(
            self.env['hr.attendance'].sudo().search_count([
                ('employee_id', '=', self.employee.id),
            ]),
            attendance_count,
        )

    def test_wfa_mode_selection_and_check_in_out_without_geofence(self):
        self.authenticate(self.login, self.password)

        modes = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/modes',
        )
        self.assertTrue(modes['success'])
        self.assertEqual(
            {item['mode'] for item in modes['data']['available_modes']},
            {'location', 'wfa'},
        )
        self.assertFalse(modes['data']['wfa_policy']['approval_required'])
        self.assertFalse(modes['data']['wfa_policy']['geofence_required'])
        self.assertTrue(modes['data']['wfa_policy']['selfie_required'])

        payload = {
            'attendance_mode': 'wfa',
            'selfie': self.selfie,
            'device_id': 'wfa-device-001',
        }
        checked_in = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/check-in', payload,
        )
        self.assertTrue(checked_in['success'])
        self.assertEqual(checked_in['data']['state'], 'checked_in')
        self.assertEqual(checked_in['data']['attendance_mode'], 'wfa')
        self.assertFalse(checked_in['data']['work_location_id'])
        self.assertFalse(checked_in['data']['validation']['geofence_valid'])
        self.assertTrue(checked_in['data']['validation']['selfie_received'])
        attendance_id = checked_in['data']['attendance_id']

        status = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/status',
        )
        self.assertEqual(status['data']['state'], 'checked_in')
        self.assertEqual(status['data']['attendance_mode'], 'wfa')

        checked_out = self.make_jsonrpc_request(
            '/api/presenly/v1/attendance/check-out', payload,
        )
        self.assertTrue(checked_out['success'])
        self.assertEqual(checked_out['data']['attendance_mode'], 'wfa')
        self.assertFalse(checked_out['data']['work_location_id'])
        self.assertFalse(checked_out['data']['validation']['geofence_valid'])
        self.assertTrue(checked_out['data']['validation']['selfie_received'])

        attendance = self.env['hr.attendance'].sudo().browse(attendance_id)
        attendance.invalidate_recordset()
        self.assertEqual(attendance.presenly_attendance_mode, 'wfa')
        self.assertFalse(attendance.presenly_work_location_id)
        self.assertTrue(attendance.check_out)

    def test_wfa_requires_selfie(self):
        self.authenticate(self.login, self.password)
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                '/api/presenly/v1/attendance/check-in', {
                    'attendance_mode': 'wfa',
                },
            )

    def test_invalid_gps_and_data_url_selfie_are_rejected_safely(self):
        attendance_count = self.env['hr.attendance'].sudo().search_count([
            ('employee_id', '=', self.employee.id),
        ])
        attachment_count = self.env['ir.attachment'].sudo().search_count([
            ('res_model', '=', 'presenly.attendance.event'),
        ])
        self.authenticate(self.login, self.password)

        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                '/api/presenly/v1/attendance/check-in', {
                    'work_location_id': self.location.id,
                    'latitude': -6.200000,
                    'longitude': 106.816666,
                    'accuracy': 0,
                    'selfie': self.selfie,
                },
            )
        with self.assertRaises(JsonRpcException):
            self.make_jsonrpc_request(
                '/api/presenly/v1/attendance/check-in', {
                    'work_location_id': self.location.id,
                    'latitude': -6.200000,
                    'longitude': 106.816666,
                    'accuracy': 8.5,
                    'selfie': f'data:image/jpeg;base64,{self.selfie}',
                },
            )

        self.env.invalidate_all()
        self.assertEqual(
            self.env['hr.attendance'].sudo().search_count([
                ('employee_id', '=', self.employee.id),
            ]),
            attendance_count,
        )
        self.assertEqual(
            self.env['ir.attachment'].sudo().search_count([
                ('res_model', '=', 'presenly.attendance.event'),
            ]),
            attachment_count,
        )
