# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class ResourceCalendarAttendance(models.Model):
    _inherit = 'resource.calendar.attendance'

    def _default_work_entry_type_id(self):
        return self.env.ref('hr_work_entry.work_entry_type_attendance', raise_if_not_found=False)

    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Work Entry Type', default=_default_work_entry_type_id)


class ResourceCalendarLeave(models.Model):
    _inherit = 'resource.calendar.leaves'

    work_entry_type_id = fields.Many2one('hr.work.entry.type', 'Work Entry Type')

    _sql_constraints = [
        ('check_calendar_leave',
         'CHECK (work_entry_type_id IS NOT NULL or resource_id IS NOT NULL)',
         'Work entry type and resource cannot be empty at the same time'),
    ]
