# Part of Odoo. See LICENSE file for full copyright and licensing details.
from datetime import datetime

from odoo.tests import HttpCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestHrAttendanceTours(HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.write({
            'attendance_validation': 'tolerance_validation',
            'attendance_validation_tolerance': 15,
            'resource_calendar_id': cls.env['resource.calendar'].create({
                'name': '40h/week',
                'attendance_ids': [
                    (0, 0, {'dayofweek': wd, 'hour_from': h, 'hour_to': h + 4})
                    for wd in ['0', '1', '2', '3', '4']
                    for h in [8, 13]
                ],
            }).id,
        })

    def _create_kiosk_attendances(self, employee, *spans):
        return self.env['hr.attendance'].create([{
            'employee_id': employee.id,
            'check_in': datetime(2024, 1, 1, *start),  # Monday, 8-12 and 13-17 expected
            'check_out': datetime(2024, 1, 1, *stop),
            'in_mode': 'kiosk',
            'out_mode': 'kiosk',
        } for start, stop in spans])

    def test_review_tour(self):
        new_test_user(self.env, login='att_manager', groups='base.group_user,hr_attendance.group_hr_attendance_user')
        employee = self.env['hr.employee'].create({'name': 'Tour Late Employee', 'tz': 'UTC'})
        late = self._create_kiosk_attendances(employee, ((9, 0), (12, 0)))
        self.assertRecordValues(late, [{'state': 'draft', 'is_late_check_in': True}])

        self.start_tour('/odoo', 'hr_attendance_review_tour', login='att_manager')
        self.assertEqual(late.state, 'validated')

    def test_my_attendance_tour(self):
        user = new_test_user(self.env, login='att_user', groups='base.group_user,hr_attendance.group_hr_attendance_own')
        employee = self.env['hr.employee'].create({'name': 'Tour User', 'tz': 'UTC', 'user_id': user.id})
        morning, afternoon = self._create_kiosk_attendances(employee, ((8, 0), (12, 0)), ((13, 0), (17, 0)))
        self.assertEqual((morning | afternoon).mapped('state'), ['validated', 'validated'])

        self.start_tour('/odoo', 'hr_attendance_my_attendance_tour', login='att_user')
        self.assertRecordValues(morning | afternoon, [
            {'state': 'validated', 'break_duration': 0},
            {'state': 'draft', 'break_duration': 0.5},
        ])
