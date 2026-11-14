# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.test_update import TestUpdateEmployeesCommon


class TestUpdateTimesheet(TestUpdateEmployeesCommon):

    def test_employee_with_timesheet_is_light_user(self):
        employee = self.env['hr.employee'].create({'name': 'Timesheeter'})
        before = self._count()
        project = self.env['project.project'].create({'name': 'Project', 'allow_timesheets': True})
        self.env['account.analytic.line'].create({
            'name': 'Work',
            'project_id': project.id,
            'employee_id': employee.id,
            'unit_amount': 1,
        })
        self.assertEqual(self._count(), before + 1)
