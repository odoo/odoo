#-*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    def _compute_amount(self):
        # Try to deduce the amount from the salary rules bound to the payslip
        overtime_work_entry_type = self.env.ref('hr_work_entry.overtime_work_entry_type', False)
        overtime_pay_percent = self.env['hr.rule.parameter'].sudo()._get_parameter_from_code('overtime_pay_percent', raise_if_not_found=False)
        if not overtime_work_entry_type or overtime_pay_percent is None or overtime_pay_percent == 100:
            super()._compute_amount()
            return
        overtime_pay_percent /= 100
        overtime_worked_days = self.env['hr.payslip.worked_days']
        for worked_day in self:
            # YTI FIXME Clean that brol, because this override is bypassing localization implementations
            if worked_day.payslip_id.struct_id.code == "USMONTHLY":
                continue
            if worked_day.work_entry_type_id != overtime_work_entry_type or worked_day.payslip_id.wage_type != 'hourly':
                continue
            overtime_worked_days |= worked_day
            amount = worked_day.payslip_id.contract_id.hourly_wage * worked_day.number_of_hours if worked_day.is_paid else 0
            worked_day.amount = amount * overtime_pay_percent
        super(HrPayslipWorkedDays, self - overtime_worked_days)._compute_amount()

    def _is_half_day(self):
        self.ensure_one()
        overtime_work_entry_type = self.env.ref('hr_work_entry.overtime_work_entry_type')
        if self.work_entry_type_id == overtime_work_entry_type:
            return False
        return super()._is_half_day()
