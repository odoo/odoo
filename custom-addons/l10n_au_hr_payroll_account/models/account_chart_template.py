# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _configure_payroll_account_au(self, companies):
        """
            |                | Credit | Debit |               Comment                |
            | -------------- | ------ | ----- | ------------------------------------ |
            | Withholding    | 21420  | 62430 | Will be reversed for negative values |
            | Net            | 21300  | 62430 |                                      |
            | Superannuation | 21400  | 62420 |                                      |
            | Child Support  | 21500  | 62460 | Will be reversed for negative values |
        """
        account_codes = [
            #  Debit
            "62430",  # Wages & Salaries
            "62460",  # Child Support
            "62420",  # Superannuation
            # Credit
            "21300",  # Wages & Salaries
            "21500",  # Child Support
            "21400",  # Superannuation
            "21420",  # PAYG Withholding
        ]
        default_account = "62430"

        # ================================================ #
        #          AU Employee Payroll Structure          #
        # ================================================ #

        structure_schedule_1 = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_regular')
        schedule_1_rule_withholding_net = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_net_structure_1")
        schedule_1_rule_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_1")
        schedule_1_rule_child_support = self.env.ref("l10n_au_hr_payroll.l10n_au_child_support_structure_1")
        schedule_1_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_1.id),
            ('code', '=', 'NET')
        ])
        #  Schedule 2
        structure_schedule_2 = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_horticulture')
        schedule_2_rule_net_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_net_structure_2")
        schedule_2_rule_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_2")
        schedule_2_rule_child_support = self.env.ref("l10n_au_hr_payroll.l10n_au_child_support_structure_2")
        schedule_2_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_2.id),
            ('code', '=', 'NET')
        ])
        #  Schedule 3 - Actor
        structure_schedule_3 = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_actor')
        schedule_3_rule_net_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_net_structure_3")
        schedule_3_rule_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_3")
        schedule_3_rule_child_support = self.env.ref("l10n_au_hr_payroll.l10n_au_child_support_structure_3")
        schedule_3_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_3.id),
            ('code', '=', 'NET')
        ])
        #  Schedule 3 - Actor Promotional
        structure_schedule_3_promo = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_actor_promotional')
        schedule_3_rule_promo_net_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_net_structure_3_promo")
        schedule_3_rule_promo_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_3_promo")
        schedule_3_rule_promo_child_support = self.env.ref("l10n_au_hr_payroll.l10n_au_child_support_structure_3_promo")
        schedule_3_rule_promo_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_3_promo.id),
            ('code', '=', 'NET')
        ])
        #  Schedule 4
        structure_schedule_4 = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_return_to_work')
        schedule_4_rule_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_total_return_to_work_structure_4")
        schedule_4_rule_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_4")
        schedule_4_rule_child_support = self.env.ref("l10n_au_hr_payroll.l10n_au_child_support_return_to_work_structure_4")
        schedule_4_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_4.id),
            ('code', '=', 'NET')
        ])
        #  Schedule 5
        structure_schedule_5 = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_lumpsum')
        schedule_5_rule_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_lumpsum_structure_5")
        schedule_5_rule_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_lumpsum_structure_5")
        schedule_5_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_5.id),
            ('code', '=', 'NET')
        ])
        #  Schedule 7 / 11
        schedule_7_11_rule_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_termination_withholding")
        schedule_7_11_rule_net = self.env.ref("l10n_au_hr_payroll.l10n_au_termination_net_salary")
        schedule_7_11_rule_child_support = self.env.ref("l10n_au_hr_payroll.l10n_au_termination_child_support")
        #  Schedule 15
        structure_schedule_15 = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_whm')
        schedule_15_rule_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_whm_structure_15")
        schedule_15_rule_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_15")
        schedule_15_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_15.id),
            ('code', '=', 'NET')
        ])
        #  No TFN
        structure_no_tfn = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_no_tfn')
        no_tfn_rule_withholding = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_net_no_tfn")
        no_tfn_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_no_tfn.id),
            ('code', '=', 'NET')
        ])

        rules_mapping = {
            # Schedule 1
            schedule_1_rule_withholding_net: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_1_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
            schedule_1_rule_super: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_1_rule_child_support: {
                "credit": "62460",
                "debit": "21500",
            },
            #  Schedule 2
            schedule_2_rule_net_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_2_rule_super: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_2_rule_child_support: {
                "credit": "62460",
                "debit": "21500",
            },
            schedule_2_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
            # Schedule 3
            schedule_3_rule_net_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_3_rule_super: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_3_rule_child_support: {
                "credit": "62460",
                "debit": "21500",
            },
            schedule_3_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
            # Shedule 3 - Promo
            schedule_3_rule_promo_net_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_3_rule_promo_child_support: {
                "credit": "62460",
                "debit": "21500",
            },
            schedule_3_rule_promo_super: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_3_rule_promo_net: {
                "credit": "21300",
                "debit": "62430",
            },
            # Schedule 4
            schedule_4_rule_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_4_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
            schedule_4_rule_super: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_4_rule_child_support: {
                "credit": "62460",
                "debit": "21500",
            },
            # Schedule 5
            schedule_5_rule_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_5_rule_super: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_5_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
            # Schedule 7 / 11
            schedule_7_11_rule_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_7_11_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
            schedule_7_11_rule_child_support: {
                "credit": "62460",
                "debit": "21500",
            },
            # Schedule 15
            schedule_15_rule_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            schedule_15_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
            schedule_15_rule_super: {
                "credit": "21400",
                "debit": "62420",
            },
            # No TFN
            no_tfn_rule_withholding: {
                "credit": "62430",
                "debit": "21420",
            },
            no_tfn_rule_net: {
                "credit": "21300",
                "debit": "62430",
            },
        }

        self._configure_payroll_account(
            companies,
            "AU",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
