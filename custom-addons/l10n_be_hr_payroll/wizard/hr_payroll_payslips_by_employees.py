# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class HrPayslipEmployees(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    def _filter_contracts(self, contracts):
        contracts = super()._filter_contracts(contracts)
        thirteen_month = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month')
        warrant = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_structure_warrant')
        double_pay = self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday')

        if self.structure_id not in thirteen_month + warrant + double_pay:
            return contracts
        mapped_contracts = defaultdict(lambda: self.env['hr.contract'])
        for contract in contracts:
            mapped_contracts[contract.employee_id] |= contract

        filtered_contracts = self.env['hr.contract']
        for employee_contracts in mapped_contracts.values():
            if len(employee_contracts) == 1:
                filtered_contracts |= employee_contracts
                continue
            # Take current contract
            filtered_contracts |= employee_contracts.sorted("date_start")[-1]
        return filtered_contracts
