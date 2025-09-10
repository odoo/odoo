# addons/hr_attendance/tests/test_hr_attendance_manager.py

from odoo.tests.common import TransactionCase, tagged
from odoo.tests import new_test_user
from odoo.exceptions import AccessError


@tagged('post_install', '-at_install')
class TestAttendanceManager(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Create a test user
        cls.marc = new_test_user(cls.env, login='marc', groups='base.group_user')
        cls.marc_employee = cls.env['hr.employee'].create({
            'name': 'Marc Employee',
            'user_id': cls.marc.id,
        })
        cls.marc_employee.attendance_manager_id = cls.marc

        # Create another employee
        cls.abigail = cls.env['hr.employee'].create({
            'name': 'Abigail Employee',
        })

    def setUp(self):
        super().setUp()
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
