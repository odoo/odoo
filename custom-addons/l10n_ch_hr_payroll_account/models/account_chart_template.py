# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import defaultdict

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_ch(self, companies):
        account_codes = [
            '5000',  # Basic Salary,
            '5003',  # Advance
            '5004',  # Holidays payment after departure
            '5005',  # 13th month
            '5006',  # Gratification
            '5007',  # Bonus, Commissions
            '5009',  # Jubilee Gift
            '5030',  # Free Meals, House, Room, Private Car
            '5031',  # Company Car Correction,
            '5040',  # Salary Allowances
            '5601',  # CA Fees
            '5700',  # AVS
            '5701',  # AC
            '5720',  # Optional LPP
            '5721',  # Optional LPP Redemption
            '5730',  # Optional AANP
            '5731',  # Optional LAAC
            '5740',  # Optional IJM, CM
            '5790',  # Withholding taxes IS
            '5820',  # Travel Expense
            '5821',  # Lunch Expense
            '5822',  # Nightly Expense
            '5830',  # Representation Fees
            '5831',  # Car Fees
            '5832',  # Other Fees
            '5840',  # Indemnities,
        ]
        default_account = '5000'
        rules_mapping = defaultdict(dict)

        # ================================================ #
        #           CH Employee Payroll Structure          #
        # ================================================ #

        basic_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_ch_hr_payroll.hr_payroll_structure_ch_employee_salary').id),
            ('code', '=', 'BASIC')
        ])
        rules_mapping[basic_rule]['credit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_basic_hourly')
        rules_mapping[rule]['credit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_advance')
        rules_mapping[rule]['credit'] = '5003'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_departure_time_off')
        rules_mapping[rule]['credit'] = '5004'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_thirteen_month')
        rules_mapping[rule]['credit'] = '5005'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_gratification')
        rules_mapping[rule]['credit'] = '5006'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_bonus')
        rules_mapping[rule]['credit'] = '5007'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_commission')
        rules_mapping[rule]['credit'] = '5007'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_jubilee_gift')
        rules_mapping[rule]['credit'] = '5009'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_sick_wage')
        rules_mapping[rule]['credit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_accident_wage')
        rules_mapping[rule]['credit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_military_wage')
        rules_mapping[rule]['credit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_ca_fee')
        rules_mapping[rule]['credit'] = '5601'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_free_meals')
        rules_mapping[rule]['credit'] = '5030'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_free_room')
        rules_mapping[rule]['credit'] = '5030'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_free_housing')
        rules_mapping[rule]['credit'] = '5030'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_company_car_employee')
        rules_mapping[rule]['credit'] = '5030'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_optional_ijm')
        rules_mapping[rule]['credit'] = '5740'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_optional_lpp')
        rules_mapping[rule]['credit'] = '5720'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_optional_lpp_redemption')
        rules_mapping[rule]['credit'] = '5721'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_optional_cm')
        rules_mapping[rule]['credit'] = '5740'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_optional_aanp')
        rules_mapping[rule]['credit'] = '5730'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_optional_laac')
        rules_mapping[rule]['credit'] = '5731'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_indemnity_apg')
        rules_mapping[rule]['credit'] = '5840'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_indemnity_ai')
        rules_mapping[rule]['credit'] = '5840'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_annuities_ai')
        rules_mapping[rule]['credit'] = '5840'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_indemnity_accident')
        rules_mapping[rule]['credit'] = '5840'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_indemnity_illness')
        rules_mapping[rule]['credit'] = '5840'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_indemnity_maternity')
        rules_mapping[rule]['credit'] = '5840'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_child_allowance')
        rules_mapping[rule]['credit'] = '5040'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_professional_training_allowance')
        rules_mapping[rule]['credit'] = '5040'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_family_allowance')
        rules_mapping[rule]['credit'] = '5040'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_birth_allowance')
        rules_mapping[rule]['credit'] = '5040'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_marriage_allowance')
        rules_mapping[rule]['credit'] = '5040'

        gross_rule = self.env['hr.salary.rule'].search([
            ('struct_id', '=', self.env.ref('l10n_ch_hr_payroll.hr_payroll_structure_ch_employee_salary').id),
            ('code', '=', 'GROSS')
        ])
        rules_mapping[gross_rule]['credit'] = '5000'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_avs')
        rules_mapping[rule]['credit'] = '5700'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_ac')
        rules_mapping[rule]['credit'] = '5701'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_compl_ac')
        rules_mapping[rule]['credit'] = '5701'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_aanp')
        rules_mapping[rule]['credit'] = '5730'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_lpp')
        rules_mapping[rule]['credit'] = '5720'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_lpp_redemption')
        rules_mapping[rule]['credit'] = '5720'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_withholding_tax')
        rules_mapping[rule]['credit'] = '5790'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_is_correction')
        rules_mapping[rule]['credit'] = '5790'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_travel_expense')
        rules_mapping[rule]['credit'] = '5820'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_car_expense')
        rules_mapping[rule]['credit'] = '5820'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_lunch_expense')
        rules_mapping[rule]['credit'] = '5821'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_nightly_expense')
        rules_mapping[rule]['credit'] = '5822'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_other_expense')
        rules_mapping[rule]['credit'] = '5820'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_representation_fees')
        rules_mapping[rule]['credit'] = '5830'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_car_fees')
        rules_mapping[rule]['credit'] = '5831'

        rule = self.env.ref('l10n_ch_hr_payroll.l10n_ch_employees_other_fees')
        rules_mapping[rule]['credit'] = '5832'

        self._configure_payroll_account(
            companies,
            "CH",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
