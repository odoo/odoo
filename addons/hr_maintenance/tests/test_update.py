# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.test_update import TestUpdateEmployeesCommon


class TestUpdateMaintenance(TestUpdateEmployeesCommon):

    def test_employee_with_maintenance_request_is_light_user(self):
        employee = self.env['hr.employee'].create({'name': 'Employee'})
        before = self._count()
        self.env['maintenance.request'].create({'name': 'Request', 'employee_id': employee.id})
        self.assertEqual(self._count(), before + 1)
