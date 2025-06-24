
from odoo.tests.common import TransactionCase
from odoo.addons.mail.tests.common import mail_new_test_user


class TestHrAttendanceManager(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.attendance_user_manager = mail_new_test_user(
            cls.env,
            name='Attendance manager',
            login='attendance_manager_1',
            email='atendance_manager_1@example.com',
            notification_type='email',
            groups='base.group_user,hr_attendance.group_hr_attendance_manager',
        )

        cls.attendance_employee = cls.env['hr.employee'].create({
            'name': 'attendance_employee',
            'attendance_manager_id': cls.attendance_user_manager.id,
        })

        cls.attendance_employee_manager = cls.env['hr.employee'].create({
            'name': 'attendance_employee_manager',
            'user_id': cls.attendance_user_manager.id,
        })

    def test_empty_manager(self):
        self.attendance_employee.write({'parent_id': False})
        self.assertFalse(self.attendance_employee.attendance_manager_id)
        self.attendance_employee.write({'parent_id': self.attendance_employee_manager.id})
        self.assertEqual(self.attendance_employee.attendance_manager_id, self.attendance_user_manager)
        self.attendance_employee.write({'parent_id': False})
        self.attendance_employee_manager.write({'user_id': False})
        self.attendance_employee.write({'parent_id': self.attendance_employee_manager.id})
        self.assertFalse(self.attendance_employee.attendance_manager_id)
