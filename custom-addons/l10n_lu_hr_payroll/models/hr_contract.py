# -*- coding:utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_lu_atn_transport = fields.Monetary("BIK Transport", help="The amount includes VAT")

    l10n_lu_extra_holidays = fields.Integer('Extra Time Off (LU)')
    l10n_lu_meal_voucher_amount = fields.Monetary('Meal Vouchers (LU)')
    l10n_lu_meal_voucher_employer_cost = fields.Monetary('Meal Voucher Employer Cost', compute='_compute_lu_meal_vouchers')
    l10n_lu_wage_with_sacrifices = fields.Monetary('Wage With Sacrifices (LU)', compute='_compute_lu_wage')

    def _get_contract_wage_field(self):
        self.ensure_one()
        if self._is_struct_from_country('LU'):
            return 'l10n_lu_wage_with_sacrifices'
        return super()._get_contract_wage_field()

    @api.depends('wage', 'l10n_lu_extra_holidays')
    def _compute_lu_wage(self):
        for contract in self:
            contract.l10n_lu_wage_with_sacrifices = contract.wage - (contract.wage / 226) * contract.l10n_lu_extra_holidays

    @api.depends('l10n_lu_meal_voucher_amount')
    def _compute_lu_meal_vouchers(self):
        # The employee always pays 2.8€ per meal voucher.
        # The employer can contribute to max 8€ per meal voucher.
        for contract in self:
            if contract.l10n_lu_meal_voucher_amount and contract.l10n_lu_meal_voucher_amount > 2.8:
                contract.l10n_lu_meal_voucher_employer_cost = min(contract.l10n_lu_meal_voucher_amount - 2.8, 8)
            else:
                contract.l10n_lu_meal_voucher_employer_cost = 0
