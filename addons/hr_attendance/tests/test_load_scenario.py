# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.tests.common import TransactionCase, new_test_user


class TestHrAttendanceScenario(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref('base.us')

    def test_load_scenario(self):
        self.env['hr.attendance']._load_demo_data()

    def test_help_data_load_demo(self):
        # the help view only proposes to load the sample data if it isn't there yet
        user = new_test_user(self.env, login='attendance_user', groups='hr_attendance.group_hr_attendance_user')
        Attendance = self.env['hr.attendance'].with_user(user)
        has_demo = self.env['ir.module.module'].search_count([('demo', '=', True)])
        self.assertEqual(Attendance.get_help_data([]), {'can_load_demo': not has_demo})
        self.env['hr.attendance']._load_demo_data()
        self.assertEqual(Attendance.get_help_data([]), {'can_load_demo': False})
