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
                    and worked_day.payslip_id.struct_id.country_id.code == "SK" \
                    and worked_day.is_paid:
                if worked_day.work_entry_type_id.code == "SICK25":
                    worked_day.amount *= 0.25
                elif worked_day.work_entry_type_id.code == "SICK55":
                    worked_day.amount *= 0.55
                elif worked_day.work_entry_type_id.code == "SICK0":
                    worked_day.amount = 0
                elif worked_day.work_entry_type_id.code == "MATERNITY":
                    worked_day.amount *= 0.75
                elif worked_day.work_entry_type_id.code == "PARENTAL":
                    worked_day.amount = 0
