# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.tests.common import tagged, HttpCase
from unittest.mock import patch
from odoo.http import Request


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
