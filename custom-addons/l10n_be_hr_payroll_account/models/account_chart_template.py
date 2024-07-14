# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_be(self, companies):
        account_codes = [
            '453000',  # Withholding taxes, IP Deduction
            '454000',  # ONSS (Employee, Employer, Miscellaneous)
            '455000',  # Due amount (net)
            '620200',  # Remuneration, Representation Fees; Private Car
            '621000',  # ONSS Employer (debit)
            '643000',  # IP
            '743000',  # Meal Vouchers
        ]
        default_account = '620200'
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #              CP200: 13th month                   #
        # ================================================ #

        basic_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id),
            ('code', '=', 'BASIC')
        ])
        rules_mapping[basic_rule]['credit'] = '455000'

        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_thirteen_month_onss_rule')
        rules_mapping[onss_rule]['credit'] = '454000'

        pp_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_thirteen_month_p_p')
        rules_mapping[pp_rule]['credit'] = '453000'

        monss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_thirteen_month_mis_ex_onss')
        rules_mapping[monss_rule]['debit'] = '454000'  # Note: this is a credit, but the amount is negative

        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_thirteen_month').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net_rule]['credit'] = '455000'

        # ================================================ #
        #              CP200: Double Holidays              #
        # ================================================ #
        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_double_holiday_onss_rule')
        rules_mapping[onss_rule]['credit'] = '454000'

        pp_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_double_holiday_pay_p_p')
        rules_mapping[pp_rule]['credit'] = '453000'

        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_double_holiday').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net_rule]['credit'] = '455000'

        # ================================================ #
        #         CP200: Employees Monthly Pay             #
        # ================================================ #

        # Remunerations
        remun_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_remuneration')
        rules_mapping[remun_rule]['debit'] = '620200'

        # IP
        ip_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_ip')
        rules_mapping[ip_rule]['debit'] = '643000'

        # ONSS (Onss - employment bonus)
        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_onss_total')
        rules_mapping[onss_rule]['credit'] = '454000'


        # Private car reimbursement
        car_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_private_car')
        rules_mapping[car_rule]['debit'] = '620200'


        # Total withholding taxes
        pp_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_withholding_taxes_total')
        rules_mapping[pp_rule]['credit'] = '453000'

        # Special Social Cotisation (MISC ONSS)
        monss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_mis_ex_onss')
        rules_mapping[monss_rule]['debit'] = '454000'  # Note: this is a credit, but the amount is negative

        # Representation Fees
        rep_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_representation_fees')
        rules_mapping[rep_rule]['debit'] = '620200'

        # IP Deduction
        ip_ded_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_ip_deduction')
        rules_mapping[ip_ded_rule]['debit'] = '453000'  # Note: This is a credit, but the amount is negative

        # Meal vouchers
        meal_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_ch_worker')
        rules_mapping[meal_rule]['debit'] = '743000'  # Note: this is a credit, but the amount is negative

        # Owed Remunerations (NET)
        net_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_be_hr_payroll.hr_payroll_structure_cp200_employee_salary').id),
            ('code', '=', 'NET')
        ])
        rules_mapping[net_rule]['credit'] = '455000'

        # ONSS Employer
        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_onss_employer')
        rules_mapping[onss_rule]['debit'] = '621000'
        rules_mapping[onss_rule]['credit'] = '454000'

        # ================================================ #
        #              CP200: Termination Fees             #
        # ================================================ #

        # Remuneration
        remun_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_remuneration')
        rules_mapping[remun_rule]['debit'] = '620200'

        # ONSS (Onss - employment bonus)
        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_onss_total')
        rules_mapping[onss_rule]['credit'] = '454000'

        # Total withholding taxes
        pp_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_salary_withholding_taxes_total')
        rules_mapping[pp_rule]['credit'] = '453000'

        # Owed Remunerations (NET)
        net_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_withholding_taxes_total')
        rules_mapping[net_rule]['credit'] = '455000'

        # ONSS Employer
        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_fees_termination_ONSS')
        rules_mapping[onss_rule]['debit'] = '621000'
        rules_mapping[onss_rule]['credit'] = '454000'

        # ================================================ #
        #              CP200: Termination Holidays N       #
        # ================================================ #

        basic_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_total_n')
        rules_mapping[basic_rule]['credit'] = '455000'

        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_rules_onss_termination')
        rules_mapping[onss_rule]['credit'] = '454000'

        monss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_rules_special_contribution_termination')
        rules_mapping[monss_rule]['credit'] = '454000'

        pp_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_rules_professional_tax_termination')
        rules_mapping[pp_rule]['credit'] = '453000'

        net_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n_pay_net_termination')
        rules_mapping[net_rule]['debit'] = '455000'

        # ================================================ #
        #        CP200: Termination Holidays N-1           #
        # ================================================ #

        basic_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_total_n')
        rules_mapping[basic_rule]['credit'] = '455000'

        onss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_rules_onss_termination')
        rules_mapping[onss_rule]['credit'] = '454000'

        monss_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_rules_special_contribution_termination')
        rules_mapping[monss_rule]['credit'] = '454000'

        pp_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_rules_professional_tax_termination')
        rules_mapping[pp_rule]['credit'] = '453000'

        net_rule = self.env.ref('l10n_be_hr_payroll.cp200_employees_termination_n1_pay_net_termination')
        rules_mapping[net_rule]['debit'] = '455000'

        self._configure_payroll_account(
            companies,
            "BE",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)

    def _configure_payroll_account_be_comp(self, companies):
        return self._configure_payroll_account_be(companies)

    def _configure_payroll_account_be_asso(self, companies):
        return self._configure_payroll_account_be(companies)
