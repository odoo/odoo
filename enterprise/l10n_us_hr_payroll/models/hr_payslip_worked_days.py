# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import models


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    def _l10n_us_get_overtime_multiplier(self):
        self.ensure_one()
        if self.work_entry_type_id.code in ("OVERTIME", "USRETROOVERTIME"):
            return 1.5
        if self.work_entry_type_id.code == "USDOUBLE":
            return 2.0
        return 1.0

    def _l10n_us_get_hourly_rate(self):
        self.ensure_one()
        if not self.is_paid or self.payslip_id.wage_type != 'hourly':
            return 0
        return self.payslip_id.contract_id.hourly_wage * self._l10n_us_get_overtime_multiplier()

    def _compute_amount(self):
        super()._compute_amount()
        for worked_day in self:
            if worked_day.payslip_id.state in ['draft', 'verify'] \
                    and not worked_day.payslip_id.edited \
                    and worked_day.payslip_id.struct_id.code == "USMONTHLY" \
                    and worked_day.is_paid:
                worked_day.amount *= worked_day._l10n_us_get_overtime_multiplier()
