
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields
from odoo.addons.hr_attendance.models.hr_attendance_overtime_rule import (_last_hours_as_intervals, _extend_intervals_for_undertime)


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

    def _get_undertime_intervals_by_date(self, date, period, overtime_quantity, attendances_by, quantity_intervals_by_date, undertime_flag):
        if period == 'day' and self.compensable_as_leave:
            missing_hours = abs(overtime_quantity)

            new_intervals = _last_hours_as_intervals(
                starting_intervals=attendances_by[period][date],
                hours=missing_hours
            )

            covered_hours = sum((end - start).total_seconds() / 3600 for (start, end, _) in new_intervals)
            if covered_hours < missing_hours:
                remaining = missing_hours - covered_hours
                new_intervals = _extend_intervals_for_undertime(
                    base_intervals=new_intervals,
                    missing_hours=remaining
                )
            for start, end, attendance in new_intervals:
                date = attendance[0].date
                quantity_intervals_by_date[date].append((start, end, self))
                undertime_flag[date, start, end] = True

            return True
        return period == 'week' and self.compensable_as_leave
