# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_ae(self, companies):
        account_codes = [
            '201002',  # Payables
            '202001',  # End of Service Provision
            '400003',  # Basic Salary
            '400004',  # Housing Allowance
            '400005',  # Transportation Allowance
            '400008',  # End of Service Indemnity
            '400012',  # Staff Other Allowances
        ]
        default_account = '400003'
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #          UAE Employee Payroll Structure          #
        # ================================================ #

        basic_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure').id),
            ('code', '=', 'BASIC')
        ], limit=1)
        rules_mapping[basic_rule]['debit'] = '400003'

        house_rule = self.env.ref('l10n_ae_hr_payroll.uae_housing_allowance_salary_rule')
        rules_mapping[house_rule]['debit'] = '400004'

        transport_rule = self.env.ref('l10n_ae_hr_payroll.uae_transportation_allowance_salary_rule')
        rules_mapping[transport_rule]['debit'] = '400005'

        other_rule = self.env.ref('l10n_ae_hr_payroll.uae_other_allowances_salary_rule')
        rules_mapping[other_rule]['debit'] = '400012'

        end_rule = self.env.ref('l10n_ae_hr_payroll.uae_end_of_service_salary_rule')
        rules_mapping[end_rule]['debit'] = '202001'

        provision_rule = self.env.ref('l10n_ae_hr_payroll.uae_end_of_service_provision_salary_rule')
        rules_mapping[provision_rule]['debit'] = '400008'
        rules_mapping[provision_rule]['credit'] = '202001'

        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_ae_hr_payroll.uae_employee_payroll_structure').id),
            ('code', '=', 'NET')
        ], limit=1)
        rules_mapping[net_rule]['credit'] = '201002'

        self._configure_payroll_account(
            companies,
            "AE",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
