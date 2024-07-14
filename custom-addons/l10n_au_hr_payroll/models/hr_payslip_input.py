# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrPayslipInput(models.Model):
    _inherit = "hr.payslip.input"

    amount = fields.Float(compute="_compute_amount", readonly=False, store=True)
    l10n_au_is_default_allowance = fields.Boolean()  # True if line is added as a default structure allowance

    @api.depends("input_type_id")
    def _compute_amount(self):
        for inpt in self:
            inpt.amount = inpt.input_type_id.l10n_au_default_amount

    @api.model_create_multi
    def create(self, vals_list):
        inputs = super().create(vals_list)
        loading_ref = self.env.ref("l10n_au_hr_payroll.input_leave_loading_lump")
        for inpt in inputs:
            if inpt.input_type_id == loading_ref and not inpt.amount:
                inpt.amount = inpt._l10n_au_get_leave_loading_lump_sum()
        return inputs

    def _l10n_au_get_leave_loading_lump_sum(self):
        self.ensure_one()
        start_year = self.payslip_id._l10n_au_get_financial_year_start(fields.Date.today())
        employee_allocations = self.env["hr.leave.allocation"].search([
            ("employee_id", "=", self.payslip_id.employee_id.id),
            ("date_from", ">=", start_year),
            ("holiday_status_id", "in", self.payslip_id.contract_id.l10n_au_leave_loading_leave_types.ids),
        ])
        year_expected_leaves = sum(employee_allocations.mapped("number_of_days_display"))
        leave_rate = self.payslip_id.contract_id.l10n_au_leave_loading_rate
        usual_daily_wage = round(self.payslip_id.get_daily_wage(), 2)
        return year_expected_leaves * (usual_daily_wage * (1 + leave_rate / 100))
