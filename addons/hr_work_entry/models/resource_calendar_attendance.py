# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    def _default_work_entry_type_id(self):
        return self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)

    work_entry_type_id = fields.Many2one(
        'hr.work.entry.type', 'Work Entry Type', default=_default_work_entry_type_id,
        groups="hr.group_hr_user")

    def _copy_attendance_vals(self):
        res = super()._copy_attendance_vals()
        res['work_entry_type_id'] = self.work_entry_type_id.id
        return res

    def _is_work_period(self):
        return not self.work_entry_type_id.is_leave and super()._is_work_period()
