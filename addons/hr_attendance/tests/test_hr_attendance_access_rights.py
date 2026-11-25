from datetime import datetime

from odoo.exceptions import AccessError
from odoo.tests import common, tagged, new_test_user


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
        cls.attendance_officer = cls.env['hr.employee'].create({
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

    def test_attendance_officer_cannot_give_attendance_to_self_without_own_right(self):
        """An officer who may not create their own attendances may not give one to themselves either."""
        managed_employee = self.env['hr.employee'].create({
            'name': 'Managed Employee',
            'attendance_manager_id': self.attendance_officer_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(self.attendance_officer_user).create({
            'employee_id': managed_employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        with self.assertRaises(AccessError):
            attendance.write({'employee_id': self.attendance_officer.id})

        self.attendance_officer_user.group_ids |= self.env.ref('hr_attendance.group_hr_attendance_own')
        attendance.write({'employee_id': self.attendance_officer.id})
        self.assertEqual(attendance.employee_id, self.attendance_officer)

    def test_attendance_officer_cannot_give_reviewed_attendance_to_self(self):
        """An officer may not review their own attendance by encoding it for an employee they approve, then giving it
        to themselves: it goes back to To Review."""
        self.env.company.attendance_validation = 'manual_validation'
        self.attendance_officer_user.group_ids |= self.env.ref('hr_attendance.group_hr_attendance_own')
        managed_employee = self.env['hr.employee'].create({
            'name': 'Managed Employee',
            'attendance_manager_id': self.attendance_officer_user.id,
        })
        attendances = self.env['hr.attendance'].with_user(self.attendance_officer_user)
        attendance = attendances.create({
            'employee_id': managed_employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'validated')
        attendance.write({'employee_id': self.attendance_officer.id})
        self.assertRecordValues(attendance, [{'employee_id': self.attendance_officer.id, 'state': 'draft'}])

        attendance.sudo().write({'employee_id': managed_employee.id, 'state': 'validated'})
        with self.assertRaises(AccessError):
            attendance.write({'employee_id': self.attendance_officer.id, 'state': 'validated'})
