# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class HrPayslipInput(models.Model):
    _inherit = "hr.payslip.input"

    amount = fields.Float(compute="_compute_amount", readonly=False, store=True)
    l10n_au_is_default_allowance = fields.Boolean()  # True if line is added as a default structure allowance
    l10n_au_payroll_code = fields.Char(related='input_type_id.l10n_au_payroll_code')
    l10n_au_payroll_code_description = fields.Selection(related='input_type_id.l10n_au_payroll_code_description')
    l10n_au_payment_type = fields.Selection(related='input_type_id.l10n_au_payment_type')

    @api.depends("input_type_id")
    def _compute_amount(self):
        for inpt in self:
            inpt.amount = inpt.input_type_id.l10n_au_default_amount

    @api.model_create_multi
    def create(self, vals_list):
        inputs = super().create(vals_list)
        loading_ref = self.env.ref("l10n_au_hr_payroll.input_leave_loading_lump")
        loading_ref_inputs = inputs.filtered(lambda i: i.input_type_id == loading_ref and not i.amount)
        leave_loading_lump_sums = self._l10n_au_get_leave_loading_lump_sums(loading_ref_inputs.payslip_id)
        if loading_ref_inputs:
            loading_ref_inputs.amount = leave_loading_lump_sums.get(loading_ref_inputs.payslip_id)
        return inputs

    @api.model
    def _l10n_au_get_leave_loading_lump_sums(self, payslips):
        res = {}
        for payslip in payslips:
            start_year = payslip.contract_id._l10n_au_get_financial_year_start(fields.Date.today())
            employee_allocations = self.env["hr.leave.allocation"].search_read([
                ("employee_id", "=", payslip.employee_id.id),
                ("date_from", ">=", start_year),
                ("holiday_status_id", "in", payslip.contract_id.l10n_au_leave_loading_leave_types.ids),
                ("date_from", "<=", payslip.contract_id.date_end or payslip.date_to),
            ], ["number_of_days_display"])
            year_expected_leaves = sum(allocation['number_of_days_display'] for allocation in employee_allocations)
            leave_rate = payslip.contract_id.l10n_au_leave_loading_rate
            usual_daily_wage = round(payslip._get_daily_wage(), 2)
            res[payslip.id] = year_expected_leaves * (usual_daily_wage * (1 + leave_rate / 100))
        return res

    @api.constrains("input_type_id", "name")
    def _check_lumpsum_e_date(self):
        lumpsum_e = self.env.ref("l10n_au_hr_payroll.l10n_au_lumpsum_e")
        for input in self.filtered(lambda x: x.input_type_id == lumpsum_e):
            if not str(input.name).isnumeric() and len(str(input.name)) != 4:
                raise ValidationError(_("The description of input Lump Sum E should be the financial year for payment."))
