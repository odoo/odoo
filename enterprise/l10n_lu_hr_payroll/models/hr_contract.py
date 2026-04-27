# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_lu_index_on_contract_signature = fields.Float(
        string='Index on Contract Signature (LU)', readonly=True, compute='_compute_indexed_wage')
    l10n_lu_indexed_wage = fields.Monetary(string='Indexed Wage (LU)', compute='_compute_indexed_wage')
    l10n_lu_current_index = fields.Float(string='Current Index (LU)', compute='_compute_indexed_wage')

    l10n_lu_meal_voucher_amount = fields.Monetary(string='Meal Vouchers (LU)')
    l10n_lu_meal_voucher_employer_cost = fields.Monetary(
        string='Meal Voucher Employer Cost (LU)', compute='_compute_l10n_lu_meal_voucher_employer_cost')

    l10n_lu_bik_vehicle = fields.Monetary(string='BIK Vehicle (LU)')
    l10n_lu_bik_vehicle_vat_included = fields.Boolean(string='BIK Vehicle VAT Included (LU)', default=True)

    l10n_lu_alw_vehicle = fields.Monetary(string='Allowance Vehicle (LU)')

    @api.depends('wage')
    def _compute_indexed_wage(self):
        for contract in self:
            contract.l10n_lu_index_on_contract_signature = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_index', date=contract.date_start, raise_if_not_found=False)
            contract.l10n_lu_current_index = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_index', raise_if_not_found=False)
            if contract.l10n_lu_index_on_contract_signature and contract.l10n_lu_current_index:
                contract.l10n_lu_indexed_wage = (
                    contract.wage if contract.wage_type == 'monthly' else contract.hourly_wage
                ) / contract.l10n_lu_index_on_contract_signature * contract.l10n_lu_current_index
            else:
                contract.l10n_lu_indexed_wage = contract.wage

    @api.depends('l10n_lu_meal_voucher_amount')
    def _compute_l10n_lu_meal_voucher_employer_cost(self):
        # The employee always pays 2.8€ per meal voucher.
        # The employer contributes for the rest up to a maximum amount.
        for contract in self:
            if contract.l10n_lu_meal_voucher_amount and contract.l10n_lu_meal_voucher_amount > 2.8:
                contract_employer_contribution = contract.l10n_lu_meal_voucher_amount - 2.8
                maximum_employer_contribution = self.env['hr.rule.parameter']._get_parameter_from_code('l10n_lu_meal_voucher_max_value') - 2.8
                contract.l10n_lu_meal_voucher_employer_cost = min(contract_employer_contribution, maximum_employer_contribution)
            else:
                contract.l10n_lu_meal_voucher_employer_cost = 0
