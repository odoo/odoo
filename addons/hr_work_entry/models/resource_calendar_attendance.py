# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.tools import format_time
from odoo.tools.date_utils import float_to_time


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Work Entry Type', store=True,
        compute='_compute_work_entry_type_id', groups="hr.group_hr_user", readonly=False)
    display_code = fields.Char(related='work_entry_type_id.display_code')
    color = fields.Integer(related='work_entry_type_id.color')

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

    def _compute_display_name(self):
        for attendance in self:
            if not attendance.work_entry_type_id:
                super()._compute_display_name()
            else:
                if attendance.duration_based:
                    attendance.display_name = self.env._("%(duration)s hours %(work_entry_type)s",
                                                        duration=format_time(self.env, float_to_time(attendance.duration_hours), time_format="HH:mm"),
                                                        work_entry_type=attendance.work_entry_type_id.display_name)
                else:
                    attendance.display_name = self.env._("%(hour_from)s - %(hour_to)s %(work_entry_type)s",
                                                        hour_from=format_time(self.env, float_to_time(attendance.hour_from), time_format="short"),
                                                        hour_to=format_time(self.env, float_to_time(attendance.hour_to), time_format="short"),
                                                        work_entry_type=attendance.work_entry_type_id.display_name)

    def _to_dict(self):
        res = super()._to_dict()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res
