# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResourceCalendarLeaves(models.Model):
    _inherit = 'resource.calendar.leaves'

    def _get_defult_resource_calendar_leave_work_entry_type(self):
        default_leave_work_entry_type = self.env['hr.work.entry.type'].search([('is_leave', '=', True)], limit=1)
        if default_leave_work_entry_type:
            return default_leave_work_entry_type
        else:
            return self.env['hr.work.entry.type'].search([], limit=1)

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', 'Work Entry Type',
        groups="hr.group_hr_user", required=True, default=_get_defult_resource_calendar_leave_work_entry_type)

    def _copy_leave_vals(self):
        res = super()._copy_leave_vals()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res
