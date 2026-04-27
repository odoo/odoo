# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_eg(self, companies):
        account_codes = [
            '201002',  # Payables
            '201026',  # Social contribution payable
            '201027',  # Income Tax
            '202001',  # end of service provision
            '400003',  # Basic Salary
            '400005',  # Transportation Allowance
            '400008',  # End of Service Indemnity
            '400012',  # Staff Other Allowances
            '400078',  # Social contribution - company portion
        ]
        default_account = '400003'
        rules_mapping = defaultdict(dict)

        rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_eg_hr_payroll.hr_payroll_structure_eg_employee_salary').id),
            ('code', '=', 'BASIC')
        ], limit=1)
        rules_mapping[rule]['debit'] = '400003'

        rule = self.env.ref('l10n_eg_hr_payroll.egypt_housing_allowance_salary_rule')
        rules_mapping[rule]['debit'] = '400005'

        rule = self.env.ref('l10n_eg_hr_payroll.egypt_other_allowances_salary_rule')
        rules_mapping[rule]['debit'] = '400012'

        rule = self.env.ref('l10n_eg_hr_payroll.egypt_social_insurance_contribution_company')
        rules_mapping[rule]['debit'] = '400078'

        rule = self.env.ref('l10n_eg_hr_payroll.egypt_social_insurance_contribution_total')
        rules_mapping[rule]['credit'] = '201026'

        rule = self.env.ref('l10n_eg_hr_payroll.egypt_end_of_service_provision_salary_rule')
        rules_mapping[rule]['debit'] = '400008'
        rules_mapping[rule]['credit'] = '202001'

        rule = self.env.ref('l10n_eg_hr_payroll.egypt_end_of_service_benefit_salary_rule')
        rules_mapping[rule]['debit'] = '202001'

        rule = self.env.ref('l10n_eg_hr_payroll.egypt_tax_bracket_total')
        rules_mapping[rule]['credit'] = '201027'

        rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_eg_hr_payroll.hr_payroll_structure_eg_employee_salary').id),
            ('code', '=', 'NET')
        ], limit=1)
        rules_mapping[rule]['credit'] = '201002'

        # ================================================ #
        #           EG Employee Payroll Structure          #
        # ================================================ #

        self._configure_payroll_account(
            companies,
            "EG",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
