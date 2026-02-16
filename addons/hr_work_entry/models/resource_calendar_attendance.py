# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Work Entry Type', store=True,
        compute='_compute_work_entry_type_id', groups="hr.group_hr_user", readonly=False)

    @api.depends('calendar_id.country_id')
    def _compute_work_entry_type_id(self):
        types_per_calendar = {}
        for resource_calendar_attendence in self:
            if not resource_calendar_attendence.work_entry_type_id and resource_calendar_attendence.calendar_id:
                calendar = resource_calendar_attendence.calendar_id
                if calendar in types_per_calendar:
                    resource_calendar_attendence.work_entry_type_id = types_per_calendar[calendar]
                else:
                    all_types = self.env['hr.work.entry.type'].sudo().search([('code', '=', 'WORK100')])
                    default_work_entry_type = all_types.filtered(
                        lambda t: t.country_id == calendar.country_id
                    ) or all_types.filtered(lambda t: not t.country_id)
                    if default_work_entry_type:
                        resource_calendar_attendence.work_entry_type_id = default_work_entry_type[0]
                        types_per_calendar[calendar] = default_work_entry_type[0]

    def _copy_attendance_vals(self):
        res = super()._copy_attendance_vals()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res

    def _is_work_period(self):
        return self.work_entry_type_id.count_as == 'working_time' and super()._is_work_period()
