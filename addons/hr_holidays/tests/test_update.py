# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr.tests.test_update import TestUpdateEmployeesCommon


class TestUpdateTimeOff(TestUpdateEmployeesCommon):

    def test_employee_with_time_off_is_light_user(self):
        employee = self.env['hr.employee'].create({'name': 'On holiday'})
        before = self._count()
        work_entry_type = self.env['hr.work.entry.type'].search([('requires_allocation', '=', False)], limit=1)
        self.env['hr.leave'].with_context(leave_skip_state_check=True).create({
            'employee_id': employee.id,
            'work_entry_type_id': work_entry_type.id,
            'request_date_from': '2026-11-02',
            'request_date_to': '2026-11-02',
        })
        self.assertEqual(self._count(), before + 1)
