# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.osv.expression import AND, OR


class HrAttendance(models.Model):
    _inherit = "hr.attendance"

    time_off = fields.Float(compute='_compute_time_off', string='Time Off', readonly=True, store=True)

    def _get_overtime_leave_domain(self):
        domain = super()._get_overtime_leave_domain()
        return AND([domain, [('holiday_id.holiday_status_id.time_type', '=', 'leave')]])

    def _get_overlap_hours(self, leave):
        start_datetime = max(self.check_in, leave.date_from)
        end_datetime = min(self.check_out, leave.date_to)
        return (end_datetime - start_datetime) / timedelta(hours=1)

    @api.depends('employee_id', 'check_in', 'check_out')
    def _compute_time_off(self):
        for attendance in self:
            if attendance.employee_id:
                domain = [
                    ('date_from', '<=', attendance.check_out),
                    ('date_to', '>=', attendance.check_in),
                ]

                time_offs = self.env['hr.leave'].search(domain)
                attendance.time_off = sum(self._get_overlap_hours(time_off) for time_off in time_offs)
            else:
                attendance.time_off = False
