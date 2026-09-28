# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def write(self, vals):
        # Versions written on employee creation are handled by the employee
        calendar_changed_versions = self.env['hr.version']
        if 'resource_calendar_id' in vals and 'employee_id' not in vals:
            calendar_changed_versions = self.filtered(lambda v: v.resource_calendar_id.id != vals['resource_calendar_id'])
        res = super().write(vals)
        calendar_changed_versions._regenerate_public_holidays_timesheets()
        return res

    def _regenerate_public_holidays_timesheets(self):
        """ Recreate the future public holidays timesheets of the employees
            whose versions changed of working schedule.
        """
        employees = self.employee_id.filtered('active').with_context(allowed_company_ids=self.company_id.ids)
        employees._delete_future_public_holidays_timesheets()
        employees._create_future_public_holidays_timesheets(employees)
