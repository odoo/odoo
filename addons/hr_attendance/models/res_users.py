# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    attendance_state = fields.Selection(related='employee_id.attendance_state')
    last_check_in = fields.Datetime(related='employee_id.last_attendance_id.check_in')
    last_check_out = fields.Datetime(related='employee_id.last_attendance_id.check_out')

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            'attendance_state',
            'last_check_in',
            'last_check_out',
        ]

    def _clean_attendance_officers(self):
        attendance_officers = self.env['hr.employee'].search(
            [('attendance_manager_id', 'in', self.ids)]).attendance_manager_id
        officers_to_remove_ids = self - attendance_officers
        if officers_to_remove_ids:
            self.env.ref('hr_attendance.group_hr_attendance_officer').user_ids = [(3, user.id) for user in
                                                                               officers_to_remove_ids]

    @api.model
    def get_overtime_data(self, domain=None, employee_id=None):
        domain = [] if domain is None else domain
        validated_overtime = {
            overtime[0].id: overtime[1]
            for overtime in self.env["hr.attendance.overtime"]._read_group(
                domain=domain + [('adjustment', '=', False)],
                groupby=['employee_id'],
                aggregates=['duration:sum']
            )
        }
        overtime_adjustments = {
            overtime[0].id: overtime[1]
            for overtime in self.env["hr.attendance.overtime"]._read_group(
                domain=domain + [('adjustment', '=', True)],
                groupby=['employee_id'],
                aggregates=['duration:sum']
            )
        }
        return {"validated_overtime": validated_overtime, "overtime_adjustments": overtime_adjustments}
