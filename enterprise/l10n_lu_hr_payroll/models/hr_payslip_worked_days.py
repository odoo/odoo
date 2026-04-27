# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class HrPayslipWorkedDays(models.Model):
    _inherit = 'hr.payslip.worked_days'

    @api.depends('is_paid', 'is_credit_time', 'number_of_hours', 'payslip_id', 'contract_id.wage', 'contract_id.l10n_lu_indexed_wage', 'payslip_id.sum_worked_hours')
    def _compute_amount(self):
        lu_worked_days = self.filtered(lambda wd: wd.payslip_id.struct_id.country_id.code == "LU")
        for worked_days in lu_worked_days:
            if worked_days.payslip_id.edited or worked_days.payslip_id.state not in ['draft', 'verify']:
                continue
            if not worked_days.contract_id or worked_days.code == 'OUT' or worked_days.is_credit_time:
                worked_days.amount = 0
                continue
            if worked_days.payslip_id.contract_id.wage_type == "monthly":
                worked_days.amount = worked_days.payslip_id.l10n_lu_prorated_wage * worked_days.number_of_hours / (worked_days.payslip_id.sum_worked_hours or 1) if worked_days.is_paid else 0
            else:
                worked_days.amount = worked_days.contract_id.l10n_lu_indexed_wage * worked_days.number_of_hours
        return super(HrPayslipWorkedDays, self - lu_worked_days)._compute_amount()
