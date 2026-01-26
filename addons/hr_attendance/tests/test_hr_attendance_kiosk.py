# Part of Odoo. See LICENSE file for full copyright and licensing details.
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.http.requestlib import Request
from odoo.tests.common import HttpCase, tagged


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
        })
        cls.employee_B = cls.env['hr.employee'].create({
            'name': 'employee_B',
            'company_id': cls.company_A.id,
            'department_id': cls.department_A.id,
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

    def test_Attendance_using_Kiosk_disabled(self):
        """All kiosk-related features should be disabled when "Attendance using Kiosk" is turned off."""

        self.company_B.attendance_using_kiosk = False
        # case 1: Accessing the Kiosk menu or onboarding action raises a UserError
        with self.assertRaises(UserError):
            self.company_B.with_company(self.company_B)._action_open_kiosk_mode()
        with self.assertRaises(UserError):
            self.env['hr.attendance'].with_company(self.company_B).action_try_kiosk()
        # case 2: Direct access to an existing Kiosk URL is blocked (403 or 404)
        response = self.url_open(
            self.company_B.attendance_kiosk_url,
            allow_redirects=False,
        )
        self.assertEqual(response.status_code, 404)
