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
                    and worked_day.payslip_id.wage_type == "monthly" \
                    and worked_day.payslip_id.struct_id.country_id.code == "PL" \
                    and worked_day.is_paid \
                    and worked_day.work_entry_type_id.code == "LEAVE110":
                worked_day.amount *= 0.80
