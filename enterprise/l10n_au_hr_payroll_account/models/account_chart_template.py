# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, _
from odoo.exceptions import UserError


class AccountChartTemplate(models.AbstractModel):
    _inherit = "account.chart.template"

    def _post_load_data(self, template_code, company, template_data):
        super()._post_load_data(template_code, company, template_data)
        # Set the superannuation current liability account
        if template_code == "au":
            clearing_house = self.env.ref('l10n_au_hr_payroll_account.res_partner_clearing_house', raise_if_not_found=False)
            if not clearing_house:
                raise UserError(_("No clearing house record found for this company!"))
            account_21400 = self.env['account.account'].with_company(company).search([
                ('company_ids', '=', company.id),
                ('code', '=', 21400)])
            clearing_house.with_company(company).property_account_payable_id = account_21400
            company.write({
                'ytd_reset_day': 1,
                'ytd_reset_month': '7',
            })

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
            "21200",  # Trade Creditors
            "21800",  # Other Deductions
        ]
        default_account = "62430"

        # ================================================ #
        #          AU Employee Payroll Structure          #
        # ================================================ #

        structure_schedule_1 = self.env.ref('l10n_au_hr_payroll.hr_payroll_structure_au_regular')
        schedule_1_rule_withholding_net = self.env.ref("l10n_au_hr_payroll.l10n_au_withholding_net_structure_1")
        schedule_1_rule_super = self.env.ref("l10n_au_hr_payroll.l10n_au_super_contribution_structure_1")
        schedule_1_rule_super_concessional = self.env.ref("l10n_au_hr_payroll.l10n_au_salary_sacrifice_structure_1")
        schedule_1_rule_child_support = self.env.ref("l10n_au_hr_payroll.l10n_au_child_support_structure_1")
        schedule_1_deductions = self.env.ref("l10n_au_hr_payroll.l10n_au_fees_and_deductions_structure_1")
        schedule_1_rule_expense_refund = self.env.ref("l10n_au_hr_payroll_account.l10n_au_salary_expense_refund_structure_1")
        schedule_1_rule_net = self.env['hr.salary.rule'].search([
            ('struct_id', '=', structure_schedule_1.id),
            ('code', '=', 'NET')
        ])

        rules_mapping = {
            # Schedule 1
            schedule_1_rule_withholding_net: {
                "credit": "62430",
                "debit": "21420",
                "debit_tags": "+W2",
                "credit_tags": "+W1",
            },
            schedule_1_rule_net: {
                "credit": "21300",
                "debit": "62430",
                "debit_tags": "+W1",
            },
            schedule_1_rule_super: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_1_rule_super_concessional: {
                "credit": "21400",
                "debit": "62420",
            },
            schedule_1_rule_child_support: {
                "credit": "62460",
                "debit": "21500",
                "credit_tags": "+W1",
            },
            schedule_1_deductions: {
                "debit": "21800",
                "credit": "62430",
            },
            schedule_1_rule_expense_refund: {
                "credit": "21300",
                "debit": "21200",
            },
        }

        self._configure_payroll_account(
            companies,
            "AU",
            account_codes=account_codes,
            rules_mapping=rules_mapping,
            default_account=default_account)
