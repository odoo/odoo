# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from odoo.tools import format_time
from odoo.tools.date_utils import float_to_time
from odoo.tools.misc import format_duration


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    time_type_id = fields.Many2one(
        'hr.time.type', 'Time Type', groups="hr.group_hr_user", index='btree_not_null',
        domain="[('id', 'in', allowed_time_type_ids)]")
    allowed_time_type_ids = fields.Many2many(
        'hr.time.type', compute='_compute_allowed_time_type_ids')
    display_code = fields.Char(related='time_type_id.display_code')
    color = fields.Integer(related='time_type_id.color')

    @api.depends('calendar_id.company_id')
    def _compute_allowed_time_type_ids(self):
        for attendance in self:
            country = attendance.calendar_id.company_id.sudo().country_id
            if not country or not self.env['hr.time.type'].search_count([('country_id', '=', country.id)], limit=1):
                domain = [('country_id', '=', False)]
            else:
                domain = [('country_id', '=', country.id)]
            attendance.allowed_time_type_ids = self.env['hr.time.type'].search(domain)

    def _compute_display_name(self):
        attendances_without_type = self.env['resource.calendar.attendance']
        for attendance in self:
            if attendance.time_type_id:
                duration = format_duration(attendance.duration_hours)
                work_entry = attendance.time_type_id.display_code or attendance.time_type_id.display_name
                if attendance.duration_based:
                    attendance.display_name = self.env._("%(duration)s hours %(time_type)s",
                                                        duration=duration,
                                                        time_type=work_entry)
                else:
                    attendance.display_name = self.env._("%(hour_from)s - %(hour_to)s (%(duration)s) %(time_type)s",
                                                        hour_from=format_time(self.env, float_to_time(attendance.hour_from), time_format="short"),
                                                        hour_to=format_time(self.env, float_to_time(attendance.hour_to), time_format="short"),
                                                        duration=duration,
                                                        time_type=work_entry)
            else:
                attendances_without_type |= attendance
        if attendances_without_type:
            super(ResourceCalendarAttendance, attendances_without_type)._compute_display_name()

    @classmethod
    def _to_dict_fields(cls):
        return super()._to_dict_fields() + ['time_type_id']

    @api.constrains('time_type_id')
    def _check_time_type_id(self):
        for calendar, attendances in self.grouped('calendar_id').items():
            time_types_countries = attendances.time_type_id.country_id
            calendar_country = calendar.country_id
            if not calendar.company_id and time_types_countries:
                raise ValidationError(self.env._("A working schedule not linked to a company cannot have a country defined on one of its time types."))

            if time_types_countries - calendar_country:
                raise ValidationError(self.env._("The country of the time types linked to the attendances must be the same as the company's country."))

    def _is_work_period(self):
        """Tell whether this attendance counts as working time.

        An attendance whose time type counts as ``absence`` (e.g. a partial incapacity
        slot) is not working time, though it stays in the schedule.

        :rtype: bool
        """
        self.ensure_one()
        time_type_sudo = self.sudo().time_type_id
        return ((not time_type_sudo) or time_type_sudo.count_as == 'working_time') and super()._is_work_period()
