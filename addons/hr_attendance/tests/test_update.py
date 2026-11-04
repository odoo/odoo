# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.test_update import TestUpdateEmployeesCommon


class TestUpdateAttendance(TestUpdateEmployeesCommon):

    def test_employee_with_attendance_is_light_user(self):
        employee = self.env['hr.employee'].create({'name': 'Employee'})
        before = self._count()
        self.env['hr.attendance'].create({'employee_id': employee.id, 'check_in': '2026-11-02 08:00:00', 'check_out': '2026-11-02 12:00:00'})
        self.assertEqual(self._count(), before + 1)
