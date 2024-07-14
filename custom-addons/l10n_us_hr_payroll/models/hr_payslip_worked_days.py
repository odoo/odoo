# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    def _compute_amount(self):
        super()._compute_amount()
        for worked_day in self:
            if worked_day.payslip_id.state in ['draft', 'verify'] \
                    and not worked_day.payslip_id.edited \
                    and worked_day.payslip_id.struct_id.code == "USMONTHLY" \
                    and worked_day.is_paid:
                if worked_day.work_entry_type_id.code == "OVERTIME":
                    worked_day.amount *= 1.5
                elif worked_day.work_entry_type_id.code == "USDOUBLE":
                    worked_day.amount *= 2.0
                elif worked_day.work_entry_type_id.code == "USRETROOVERTIME":
                    worked_day.amount *= 1.5
