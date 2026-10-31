# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.tests.common import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestHrAttendanceSystray(HttpCase):
    """ Tests for the systray check in/out JSON route. """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({'name': 'systray_company'})

        # A user linked to an employee: the regular check in/out case.
        cls.user_with_employee = cls.env['res.users'].create({
            'name': 'user_with_employee',
            'login': 'user_with_employee',
            'password': 'user_with_employee',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, cls.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })
        cls.employee = cls.env['hr.employee'].create({
            'name': 'employee_with_user',
            'company_id': cls.company.id,
            'user_id': cls.user_with_employee.id,
        })

        # A user with no linked employee: the previously crashing case.
        cls.user_without_employee = cls.env['res.users'].create({
            'name': 'user_without_employee',
            'login': 'user_without_employee',
            'password': 'user_without_employee',
            'company_id': cls.company.id,
            'company_ids': [(6, 0, cls.company.ids)],
            'group_ids': [(6, 0, [cls.env.ref('base.group_user').id])],
        })

    def test_systray_check_in_out_without_employee(self):
        """ A user without a linked employee must not trigger a 500 (singleton
        ValueError); the route returns gracefully with an empty payload. """
        self.assertFalse(self.user_without_employee.employee_id)
        self.authenticate('user_without_employee', 'user_without_employee')
        result = self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', {})
        self.assertEqual(result, {})

    def test_systray_check_in_out_with_employee(self):
        """ Control case: a user with a linked employee checks in normally. """
        self.assertEqual(self.employee.attendance_state, 'checked_out')
        self.authenticate('user_with_employee', 'user_with_employee')
        result = self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', {})
        self.assertTrue(result)
        self.assertEqual(result['employee_name'], 'employee_with_user')
        self.assertEqual(self.employee.attendance_state, 'checked_in')

    def test_systray_check_in_records_device_with_or_without_tracking(self):
        """The IP address, browser and location are recorded whether location tracking is enabled
        or not: tracking only adds the precise position sent by the device."""
        self.authenticate('user_with_employee', 'user_with_employee')
        chrome = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'}
        position = {'latitude': 50.8466, 'longitude': 4.3528}
        Geocoder = self.registry['base.geocoder']
        for tracking in (False, True):
            with self.subTest(tracking=tracking), \
                    patch.object(Geocoder, '_get_localisation', lambda self, latitude, longitude: 'Brussels'):
                self.company.attendance_device_tracking = tracking
                self.env.flush_all()
                self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', position, headers=chrome)
                attendance = self.employee.last_attendance_id
                self.assertRecordValues(attendance, [{
                    'in_location': 'Brussels',
                    'in_ip_address': '127.0.0.1',
                    'in_browser': 'chrome',
                    'in_latitude': 50.8466 if tracking else 0,
                }])
                self.make_jsonrpc_request('/hr_attendance/systray_check_in_out', position, headers=chrome)
                self.assertRecordValues(attendance, [{'out_ip_address': '127.0.0.1', 'out_browser': 'chrome'}])
                # the next check-in can fall in the same second as this one, which would stay the last attendance
                attendance.unlink()
