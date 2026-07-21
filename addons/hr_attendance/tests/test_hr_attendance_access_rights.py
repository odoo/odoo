from datetime import datetime

from odoo.exceptions import AccessError
from odoo.tests import common, tagged, new_test_user

MAIL_OFF = {
    'tracking_disable': True,
    'mail_create_nosubscribe': True,
    'mail_create_nolog': True,
    'mail_notrack': True,
}


@tagged('access_rights', 'post_install', '-at_install')
class TestHrAttendanceAccessRights(common.TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.attendance_officer_user = new_test_user(
            cls.env,
            login='attendance_officer',
            groups='hr_attendance.group_hr_attendance_officer',
        )
        cls.attendance_officer = cls.env['hr.employee'].with_context(**MAIL_OFF).create({
            'name': 'Attendance Officer Employee',
            'user_id': cls.attendance_officer_user.id,
        })

    def test_attendance_officer_cannot_self_edit(self):
        with self.assertRaises(AccessError):
            self.env['hr.attendance'].with_user(self.attendance_officer_user).create({
                'employee_id': self.attendance_officer.id,
                'check_in': datetime(2025, 1, 1, 8, 0, 0),
                'check_out': datetime(2025, 1, 1, 17, 0, 0),
            })
