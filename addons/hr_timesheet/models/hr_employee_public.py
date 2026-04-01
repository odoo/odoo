# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployeePublic(models.Model):
    _inherit = 'hr.employee.public'

    has_timesheet = fields.Boolean(related='employee_id.has_timesheet')

    def action_timesheet_from_employee(self):
        self.ensure_one()
        if self.is_user:
            return self.employee_id.action_timesheet_from_employee()
