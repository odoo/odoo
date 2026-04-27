# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.hr_contract_salary.controllers import main


class HrContractSalary(main.HrContractSalary):

    def _get_wage_to_apply(self):
        return "l10n_be_wage_with_mobility_budget"

    def _get_compute_results(self, new_contract):
        result = super()._get_compute_results(new_contract)
        result['l10n_be_mobility_budget_amount_monthly'] = new_contract.l10n_be_mobility_budget_amount_monthly
        result['l10n_be_wage_with_mobility_budget'] = new_contract.l10n_be_wage_with_mobility_budget
        return result
