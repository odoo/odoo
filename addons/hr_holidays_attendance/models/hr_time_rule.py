# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrTimeRule(models.Model):
    _inherit = 'hr.time.rule'

    condition_work_entry_type_ids = fields.Many2many(
        default=lambda self: self.env.ref('hr_work_entry.attendance_work_entry_type', raise_if_not_found=False),
    )

    def _get_remainder_leave_vals(self, employee, source_leave, date_from, date_to):
        vals = super()._get_remainder_leave_vals(employee, source_leave, date_from, date_to)
        if source_leave.attendance_id:
            vals['attendance_id'] = source_leave.attendance_id.id
        return vals

    def _get_output_leave_vals(self, employee, rule, date_from, date_to, source_leave, all_rules=None):
        vals = super()._get_output_leave_vals(employee, rule, date_from, date_to, source_leave, all_rules=all_rules)
        if source_leave.attendance_id:
            vals['attendance_id'] = source_leave.attendance_id.id
        return vals
