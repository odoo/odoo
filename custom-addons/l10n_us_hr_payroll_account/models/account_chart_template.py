# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_generic_coa(self, companies):
        account_codes = [
            '6300',  # Salary Expenses
            '2300',  # Salaries Payable,
            '2301',  # Employee Payroll Taxes
            '2302',  # Employer Payroll Taxes
        ]
        default_account = '6300'
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #           US Employee Payroll Structure          #
        # ================================================ #

        gross_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_us_hr_payroll.hr_payroll_structure_us_employee_salary').id),
            ('code', '=', 'GROSS')
        ])
        rules_mapping[gross_rule]['debit'] = '6300'

        fit_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_federal_income_tax')
        rules_mapping[fit_rule]['debit'] = '2301'

        sst_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_social_security_tax')
        rules_mapping[sst_rule]['debit'] = '2301'

        medicare_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_medicare_tax')
        rules_mapping[medicare_rule]['debit'] = '2301'

        medicare_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_medicare_additional_tax')
        rules_mapping[medicare_rule]['debit'] = '2301'

        ca_income_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_ca_state_income_tax')
        rules_mapping[ca_income_rule]['debit'] = '2301'

        ca_sdi_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_ca_sdi_tax')
        rules_mapping[ca_sdi_rule]['debit'] = '2301'

        ny_income_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_ny_state_income_tax')
        rules_mapping[ny_income_rule]['debit'] = '2301'

        ny_sdi_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_ny_sdi_tax')
        rules_mapping[ny_sdi_rule]['debit'] = '2301'

        ny_pfl_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_ny_pfl_tax')
        rules_mapping[ny_pfl_rule]['debit'] = '2301'

        ny_reimployment_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_ny_reimployment_tax')
        rules_mapping[ny_reimployment_rule]['debit'] = '6300'
        rules_mapping[ny_reimployment_rule]['credit'] = '2302'

        company_sst_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_company_social_security')
        rules_mapping[company_sst_rule]['debit'] = '6300'
        rules_mapping[company_sst_rule]['credit'] = '2302'

        company_medicare_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_company_medicare')
        rules_mapping[company_medicare_rule]['debit'] = '6300'
        rules_mapping[company_medicare_rule]['credit'] = '2302'

        company_futa_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_company_futa')
        rules_mapping[company_futa_rule]['debit'] = '6300'
        rules_mapping[company_futa_rule]['credit'] = '2302'

        company_ca_sui_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_company_sui')
        rules_mapping[company_ca_sui_rule]['debit'] = '6300'
        rules_mapping[company_ca_sui_rule]['credit'] = '2302'

        company_ca_sui_rule = self.env.ref('l10n_us_hr_payroll.l10n_us_employee_salary_company_ca_ett')
        rules_mapping[company_ca_sui_rule]['debit'] = '6300'
        rules_mapping[company_ca_sui_rule]['credit'] = '2302'

        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_us_hr_payroll.hr_payroll_structure_us_employee_salary').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net_rule]['credit'] = '2300'

        self._configure_payroll_account(
            companies,
            "US",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
