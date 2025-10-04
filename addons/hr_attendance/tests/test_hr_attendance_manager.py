# addons/hr_attendance/tests/test_attendance_manager.py

from odoo.tests.common import TransactionCase, tagged
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestAttendanceManager(TransactionCase):

    def setUp(self):
        super().setUp()
        # Fetch Marc Demo (demo user)
        self.marc = self.env.ref("base.user_demo")
        self.marc_employee = self.marc.employee_id
        self.marc_employee.attendance_manager_id = self.marc

        # Fetch another employee (e.g., Abigail)
        self.abigail = self.env.ref("hr.employee_hne")

        # Create an attendance for Marc Demo's employee
        self.attendance = self.env['hr.attendance'].create({
            'employee_id': self.marc_employee.id,
            'check_in': '2025-09-09 08:00:00',
            'check_out': '2025-09-09 12:00:00',
        })

    def test_cannot_change_employee_without_manager_rights(self):
        """Marc Demo should NOT be able to change the employee on his attendance
        if he is not assigned as attendance manager of that employee.
        """
        attendance_as_marc = self.attendance.with_user(self.marc)
        with self.assertRaises(AccessError):
            attendance_as_marc.write({'employee_id': self.abigail.id})

    def test_can_change_employee_with_manager_rights(self):
        """Marc Demo should be able to change the employee on attendance
        once he is set as attendance manager of Abigail.
        """
        # Assign Marc Demo as attendance manager of Abigail
        self.abigail.attendance_manager_id = self.marc

        attendance_as_marc = self.attendance.with_user(self.marc)
        # This should succeed now
        attendance_as_marc.write({'employee_id': self.abigail.id})

        # Verify the employee_id has actually changed
        self.assertEqual(attendance_as_marc.employee_id, self.abigail)
