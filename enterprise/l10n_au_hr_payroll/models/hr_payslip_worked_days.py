# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class HrPayslipWorkedDays(models.Model):
    _inherit = "hr.payslip.worked_days"

    def _compute_amount(self):
        res = super()._compute_amount()
        for wd in self:
            if not wd.payslip_id.contract_id or not wd.payslip_id.contract_id._is_struct_from_country("AU"):
                continue
            # The complete duration of contract not met (Pay for the hours worked)
            if wd.payslip_id.date_from + wd.payslip_id._get_schedule_timedelta() != wd.payslip_id.date_to:
                wage = wd.payslip_id.contract_id.hourly_wage if wd.payslip_id.contract_id else 0
                wd.amount = wage * wd.number_of_hours
            uses_leave_loading = wd.contract_id.l10n_au_leave_loading == "regular" and wd.work_entry_type_id.code == 'AU.PT'
            if not wd.payslip_id.edited and wd.is_paid and uses_leave_loading:
                wd.amount *= 1 + (wd.contract_id.l10n_au_leave_loading_rate / 100)
                continue
            rate = 1 + wd.work_entry_type_id.l10n_au_penalty_rate
            if wd.work_entry_type_id.l10n_au_work_stp_code != 'T':  # Casual loading is not applicable to Overtime hours
                rate += wd.contract_id.l10n_au_casual_loading
            wd.amount *= rate
        return res

    def _get_l10n_au_hourly_rate(self):
        self.ensure_one()
        if not self or not self.payslip_id.contract_id._is_struct_from_country("AU"):
            return 0
        if self.payslip_id.date_from + self.payslip_id._get_schedule_timedelta() != self.payslip_id.date_to \
            or self.payslip_id.wage_type == "hourly":
            wage = self.payslip_id.contract_id.hourly_wage
        else:
            wage = self.payslip_id.contract_id.contract_wage / (self.payslip_id._get_regular_worked_hours() or 1) if self.is_paid else 0

        uses_leave_loading = self.contract_id.l10n_au_leave_loading == "regular" and self.work_entry_type_id.code == 'AU.PT'
        if not self.payslip_id.edited and self.is_paid and uses_leave_loading:
            wage *= 1 + (self.contract_id.l10n_au_leave_loading_rate / 100)
            return wage
        rate = 1 + self.work_entry_type_id.l10n_au_penalty_rate
        if self.work_entry_type_id.l10n_au_work_stp_code != 'T':
            rate += self.contract_id.l10n_au_casual_loading
        return wage * rate
