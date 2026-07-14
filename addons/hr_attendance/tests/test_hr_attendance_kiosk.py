# Part of Odoo. See LICENSE file for full copyright and licensing details.
import json
from datetime import timedelta
from unittest.mock import patch

from odoo import fields
from odoo.http.requestlib import Request
from odoo.tests.common import HttpCase, JsonRpcException, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'hr_attendance_overtime')
class TestHrAttendanceKiosk(HttpCase):
    """ Tests for kiosk """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_A = cls.env['res.company'].create({'name': 'company_A'})
        cls.company_B = cls.env['res.company'].create({'name': 'company_B'})

        cls.department_A = cls.env['hr.department'].create({'name': 'department_A', 'company_id': cls.company_B.id})

        cls.employee_A = cls.env['hr.employee'].create({
            'name': 'employee_A',
            'company_id': cls.company_B.id,
            'department_id': cls.department_A.id,
            'barcode': 'EMPLOYEEA123',
            'pin': '1234',
        })
        cls.employee_B = cls.env['hr.employee'].create({
            'name': 'employee_B',
            'company_id': cls.company_A.id,
            'department_id': cls.department_A.id,
        })
        cls.company_B.attendance_break_management = True

    def _create_checked_out_attendance(self, employee=None):
        employee = employee or self.employee_A
        now = fields.Datetime.now()
        return self.env['hr.attendance'].create({
            'employee_id': employee.id,
            'check_in': now - timedelta(hours=2),
            'check_out': now - timedelta(hours=1),
        })

    def _update_break(self, **params):
        return self.make_jsonrpc_request('/hr_attendance/update_break_duration', {
            'token': self.company_B.attendance_kiosk_key,
            **params,
        })

    def test_employee_count_kiosk(self):
        # the mock need to return a None value which can be converted into a Reponse object
        with patch.object(Request, "render", return_value=None) as render:
            self.url_open(self.company_B.attendance_kiosk_url)

        render.assert_called_once()
        _template, kiosk_info = render.call_args[0]
        kiosk_info = kiosk_info['kiosk_backend_info']
        self.assertEqual(kiosk_info['company_name'], 'company_B')
        self.assertEqual(kiosk_info['departments'][0]['count'], 1)

    def test_employee_infos_on_kiosk(self):
        with patch.object(Request, "render", return_value=None) as render:
            self.url_open(self.company_B.attendance_kiosk_url)
        _template, kiosk_info = render.call_args[0]

        kiosk_info = kiosk_info['kiosk_backend_info']
        token = kiosk_info.get('token')
        domain = ['&', ('department_id', '=', self.department_A.id), ('name', 'ilike', 'employee')]

        # search the employee with department
        response = self.url_open(
            url='/hr_attendance/employees_infos',
            data=json.dumps({
                'params': {
                    'token': token,
                    'limit': 10,
                    'offset': 0,
                    'domain': domain,
                },
            }),
            headers={'Content-Type': 'application/json'},
        )
        result = json.loads(response.content).get('result')
        self.assertTrue(result['records'])

    def test_update_break_duration_checks_identification_and_attendance(self):
        attendance = self._create_checked_out_attendance()
        self.company_B.attendance_kiosk_use_pin = True

        self.assertFalse(self._update_break(
            employee_id=self.employee_A.id,
            pin_code='wrong',
            attendance_id=attendance.id,
            break_duration=0.5,
        ))
        self.assertFalse(self._update_break(
            employee_id=self.employee_B.id,
            attendance_id=attendance.id,
            break_duration=0.5,
        ))
        self.assertFalse(self.make_jsonrpc_request('/hr_attendance/update_break_duration', {
            'token': 'invalid',
            'barcode': self.employee_A.barcode,
            'attendance_id': attendance.id,
            'break_duration': 0.5,
        }))
        result = self._update_break(
            barcode=self.employee_A.barcode,
            attendance_id=attendance.id,
            break_duration=0.5,
        )
        self.assertTrue(result['attendance'])
        self.assertEqual(attendance.break_duration, 0.5)

    def test_update_break_duration_only_updates_last_closed_attendance(self):
        previous_attendance = self._create_checked_out_attendance()
        now = fields.Datetime.now()
        latest_attendance = self.env['hr.attendance'].create({
            'employee_id': self.employee_A.id,
            'check_in': now - timedelta(minutes=30),
        })

        self.assertFalse(self._update_break(
            employee_id=self.employee_A.id,
            attendance_id=previous_attendance.id,
            break_duration=0.5,
        ))
        self.assertFalse(self._update_break(
            employee_id=self.employee_A.id,
            attendance_id=latest_attendance.id,
            break_duration=0.5,
        ))
        latest_attendance.check_out = now
        with self.assertRaises(JsonRpcException), mute_logger('odoo.http'):
            self._update_break(
                employee_id=self.employee_A.id,
                attendance_id=latest_attendance.id,
                break_duration=1,
            )

    def test_update_break_duration_does_not_change_manager_approved_attendance(self):
        attendance = self._create_checked_out_attendance()
        self.company_B.attendance_overtime_validation = 'by_manager'
        self.env['hr.attendance.overtime.line'].create({
            'attendance_id': attendance.id,
            'date': attendance.date,
            'duration': 0.5,
            'status': 'approved',
        })

        result = self._update_break(
            employee_id=self.employee_A.id,
            attendance_id=attendance.id,
            break_duration=0.5,
        )

        self.assertFalse(result)
        self.assertFalse(attendance.break_duration)
