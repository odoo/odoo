from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError
from datetime import date, datetime
from odoo.tests import new_test_user


@tagged('hr_attendance_self_edit_role')
@tagged('at_install', '-post_install')
class TestHrAttendanceSelfEdit(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'SweatChipChop Inc.',
            'attendance_overtime_validation': 'no_validation',
        })

        cls.admin = new_test_user(cls.env, login='user_admin', groups='hr_attendance.group_hr_attendance_manager', company_id=cls.company.id).with_company(cls.company)

        cls.user_self_edit = new_test_user(cls.env, login='user_self_edit', groups='hr_attendance.group_hr_attendance_own', company_id=cls.company.id).with_company(cls.company)
        cls.emp_self_edit = cls.env['hr.employee'].create({
            'name': "Youssef Ahmed",
            'user_id': cls.user_self_edit.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
        })

        cls.user_other = new_test_user(cls.env, login='user_other', groups='base.group_user', company_id=cls.company.id).with_company(cls.company)
        cls.emp_other = cls.env['hr.employee'].create({
            'name': "Ali Mohammed",
            'user_id': cls.user_other.id,
            'company_id': cls.company.id,
            'tz': 'UTC',
            'date_version': date(2020, 1, 1),
            'contract_date_start': date(2020, 1, 1),
        })

    def test_01_self_edit_own_attendance(self):
        """ Test a user with 'own' group can create and edit their own record """
        attendance = self.env['hr.attendance'].with_user(self.user_self_edit).create({
            'employee_id': self.emp_self_edit.id,
            'check_in': datetime(2023, 1, 1, 8, 0),
            'check_out': datetime(2023, 1, 1, 16, 0),
        })

        attendance._compute_can_edit()
        self.assertTrue(attendance.can_edit, "User should be able to edit their own pending attendance")

        attendance.write({'check_out': datetime(2023, 1, 1, 17, 0)})
        self.assertEqual(attendance.check_out, datetime(2023, 1, 1, 17, 0))

    def test_02_restrict_other_attendance(self):
        """ Test a user with 'own' group cannot edit someone else's attendance """
        attendance_other = self.env['hr.attendance'].create({
            'employee_id': self.emp_other.id,
            'check_in': datetime(2023, 1, 1, 8, 0),
            'check_out': datetime(2023, 1, 1, 16, 0),
        })

        with self.assertRaises(AccessError):
            attendance_other.with_user(self.user_self_edit).write({
                'check_out': datetime(2023, 1, 1, 18, 0)
            })

    def test_03_approved_restriction(self):
        """ Test a user with 'own' group cannot edit if status is approved and validation is manager_validation """
        self.company.attendance_overtime_validation = 'by_manager'
        attendance = self.env['hr.attendance'].with_user(self.user_self_edit).create({
            'employee_id': self.emp_self_edit.id,
            'check_in': datetime(2023, 1, 1, 8, 0),
            'check_out': datetime(2023, 1, 1, 17, 0),
        })
        attendance.with_user(self.user_self_edit)._compute_can_edit()
        self.assertTrue(attendance.can_edit, "User should be able to edit while not yet approved")

        attendance.with_user(self.admin).write({
            'overtime_status': 'approved'
        })
        attendance_as_user = attendance.with_user(self.user_self_edit)
        attendance_as_user._compute_can_edit()
        self.assertEqual(attendance.overtime_status, 'approved', "Status should be approved")
        self.assertFalse(attendance_as_user.can_edit, "Employee should NOT be able to edit once manager has approved")
