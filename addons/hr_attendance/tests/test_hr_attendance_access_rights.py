from datetime import datetime

from odoo.exceptions import AccessError, UserError
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

    def test_self_edit_user_can_create_under_manual_validation(self):
        self.env.company.attendance_validation = 'manual_validation'
        self_edit_user = new_test_user(
            self.env,
            login='self_edit_user',
            groups='hr_attendance.group_hr_attendance_own',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Self Edit Employee',
            'user_id': self_edit_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(self_edit_user).create({
            'employee_id': employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')
        attendance_as_user = attendance.with_user(self_edit_user)
        attendance_as_user.invalidate_recordset()
        self.assertTrue(attendance_as_user.wet_display_code or attendance_as_user.work_entry_type_id.name)

    def test_officer_with_self_edit_can_create_own_attendance_under_manual_validation(self):
        self.env.company.attendance_validation = 'manual_validation'
        officer_user = new_test_user(
            self.env,
            login='officer_with_self_edit',
            groups='hr_attendance.group_hr_attendance_officer,hr_attendance.group_hr_attendance_own',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Officer With Self Edit Employee',
            'user_id': officer_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(officer_user).create({
            'employee_id': employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')

    def test_officer_managing_employee_still_auto_validates(self):
        """an officer creating an attendance for an employee they actually
        manage auto-validates it, even under manual approval."""
        self.env.company.attendance_validation = 'manual_validation'
        managed_employee = self.env['hr.employee'].create({
            'name': 'Managed Employee',
            'attendance_manager_id': self.attendance_officer_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(self.attendance_officer_user).create({
            'employee_id': managed_employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'validated')

    def test_officer_cannot_validate_own_attendance(self):
        """an officer must not be able to validate/refuse their own attendance just
        because they hold officer rights over OTHER employees"""
        officer_user = new_test_user(
            self.env,
            login='officer_cannot_self_validate',
            groups='hr_attendance.group_hr_attendance_officer,hr_attendance.group_hr_attendance_own',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Officer Cannot Self Validate Employee',
            'user_id': officer_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(officer_user).create({
            'employee_id': employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
            'state': 'draft',
        })
        with self.assertRaises(UserError):
            attendance.with_user(officer_user).action_validate()
        with self.assertRaises(UserError):
            attendance.with_user(officer_user).action_refuse()
        self.assertEqual(attendance.state, 'draft')

    def test_officer_can_validate_managed_employee_attendance(self):
        """an officer can validate/refuse an attendance belonging
        to an employee they actually manage."""
        managed_employee = self.env['hr.employee'].create({
            'name': 'Managed Employee For Validation',
            'attendance_manager_id': self.attendance_officer_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(self.attendance_officer_user).create({
            'employee_id': managed_employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
            'state': 'draft',
        })
        attendance.with_user(self.attendance_officer_user).action_validate()
        self.assertEqual(attendance.state, 'validated')

    def test_self_edit_user_cannot_bypass_review_via_direct_write(self):
        self.env.company.attendance_validation = 'manual_validation'
        self_edit_user = new_test_user(
            self.env,
            login='self_edit_bypass_attempt',
            groups='hr_attendance.group_hr_attendance_own',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Self Edit Bypass Employee',
            'user_id': self_edit_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(self_edit_user).create({
            'employee_id': employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')
        with self.assertRaises(UserError):
            attendance.with_user(self_edit_user).write({'state': 'validated'})
        self.assertEqual(attendance.state, 'draft')

    def test_tolerance_auto_validation_still_works_for_self_edit_user(self):
        self.env.company.write({
            'attendance_validation': 'tolerance_validation',
            'attendance_validation_tolerance': 100,
        })
        self_edit_user = new_test_user(
            self.env,
            login='self_edit_tolerance',
            groups='hr_attendance.group_hr_attendance_own',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Self Edit Tolerance Employee',
            'user_id': self_edit_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(self_edit_user).create({
            'employee_id': employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.state, 'validated')

    def test_attendance_admin_can_manage_work_entry_types(self):
        admin_user = new_test_user(
            self.env,
            login='attendance_admin',
            groups='hr_attendance.group_hr_attendance_user',
        )
        work_entry_type = self.env['hr.work.entry.type'].with_user(admin_user).create({
            'name': 'Test Time Type',
            'code': 'TESTWET',
        })
        work_entry_type.with_user(admin_user).name = 'Test Time Type Renamed'

    def test_narrow_officer_cannot_manage_work_entry_types(self):
        with self.assertRaises(AccessError):
            self.env['hr.work.entry.type'].with_user(self.attendance_officer_user).create({
                'name': 'Should Not Be Allowed',
                'code': 'NOPE',
            })

    def test_self_edit_user_can_check_in_and_out_under_manual_validation(self):
        """simulate the systray check-in/check-out flow"""
        self.env.company.attendance_validation = 'manual_validation'
        self_edit_user = new_test_user(
            self.env,
            login='self_edit_user_2',
            groups='hr_attendance.group_hr_attendance_own',
        )
        employee = self.env['hr.employee'].create({
            'name': 'Self Edit Employee 2',
            'user_id': self_edit_user.id,
        })
        attendance = self.env['hr.attendance'].with_user(self_edit_user).create({
            'employee_id': employee.id,
            'check_in': datetime(2025, 1, 1, 8, 0, 0),
        })
        self.assertEqual(attendance.state, 'draft')
        attendance.with_user(self_edit_user).write({
            'check_out': datetime(2025, 1, 1, 17, 0, 0),
        })
        self.assertEqual(attendance.check_out, datetime(2025, 1, 1, 17, 0, 0))
