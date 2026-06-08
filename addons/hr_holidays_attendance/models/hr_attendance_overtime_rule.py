
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertimeRule(models.Model):
    _name = 'hr.attendance.overtime.rule'
    _inherit = 'hr.attendance.overtime.rule'

    compensable_as_leave = fields.Boolean("Give back as time off", default=False)
    leave_compensation_rate = fields.Float(default=1.0)

    def _extra_overtime_vals(self):

        cal_rules = self.filtered('compensable_as_leave')

        total_leave_compensation_rate = 0.0
        if cal_rules:
            if self.ruleset_id.rate_combination_mode == 'sum':
                total_leave_compensation_rate = sum((r.leave_compensation_rate - 1.0 for r in cal_rules), start=1.0)
            elif self.ruleset_id.rate_combination_mode == 'max':
                total_leave_compensation_rate = max(r.leave_compensation_rate for r in cal_rules)

        return {
            **super()._extra_overtime_vals(),
            'compensable_as_leave': any(self.mapped('compensable_as_leave')),
            'leave_compensation_rate': total_leave_compensation_rate,
        }
