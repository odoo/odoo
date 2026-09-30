
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields


class HrAttendanceOvertimeRule(models.Model):
    _name = 'hr.attendance.overtime.rule'
    _inherit = 'hr.attendance.overtime.rule'

    compensable_as_leave = fields.Boolean("Give back as time off", default=False)

    def _extra_overtime_vals(self):
        if not self:
            return {
                **super()._extra_overtime_vals(),
                'compensable_as_leave': False,
            }

        res = super()._extra_overtime_vals()
        res['compensable_as_leave'] = any(self.mapped('compensable_as_leave'))
        if self.ruleset_id.rate_combination_mode == 'sum' and any(self.mapped('paid')):
            combined_rate = 1.0
            combined_rate += sum(r.amount_rate - 1.0 for r in self.filtered(
                lambda r: r.paid and not r.compensable_as_leave
            ))
            combined_rate += sum(r.amount_rate for r in self.filtered(
                lambda r: r.paid and r.compensable_as_leave
            ))
            res['amount_rate'] = combined_rate
        return res
