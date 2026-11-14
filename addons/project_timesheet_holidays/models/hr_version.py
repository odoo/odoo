# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import datetime, time

from odoo import models


class HrVersion(models.Model):
    _inherit = 'hr.version'

    def write(self, vals):
        # Versions written on employee creation are handled by the employee
        calendar_changed_versions = self.env['hr.version']
        old_resource_calendars = self.mapped('resource_calendar_id')
        if 'resource_calendar_id' in vals and 'employee_id' not in vals:
            calendar_changed_versions = self.filtered(lambda v: v.resource_calendar_id.id != vals['resource_calendar_id'])
        res = super().write(vals)
        calendar_changed_versions and calendar_changed_versions._regenerate_public_holidays_timesheets(old_resource_calendars)
        return res

    def _regenerate_public_holidays_timesheets(self, old_resource_calendars=None):
        """ Recreate the public holidays timesheets of the employees whose
            versions changed of working schedule, over the whole version period.
        """
        versions = self.sudo()
        domain = [
            ('resource_id', '=', False),
            ('company_id', 'in', versions.company_id.ids),
            ('company_id.internal_project_id', '!=', False),
            ('company_id.leave_timesheet_task_id', '!=', False),
            ('calendar_id', 'in', [False] + versions.resource_calendar_id.ids + old_resource_calendars.ids),
            ('date_to', '>=', datetime.combine(min(versions.mapped('date_start')), time.min)),
        ]
        # The last version of an employee has no end date, so no upper bound
        date_ends = versions.mapped('date_end')
        if all(date_ends):
            domain.append(('date_from', '<=', datetime.combine(max(date_ends), time.max)))
        global_leaves = self.env['resource.calendar.leaves'].sudo().search(domain)
        timesheets = global_leaves.timesheet_ids
        timesheets.write({'global_leave_id': False})
        timesheets.unlink()
        global_leaves.with_context(allowed_company_ids=self.company_id.ids)._generate_timesheeets()
