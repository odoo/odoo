# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_ke_pension_contribution = fields.Monetary("Pension Contribution")

    l10n_ke_food_allowance = fields.Monetary("Food Allowance")
    l10n_ke_airtime_allowance = fields.Monetary("Airtime Allowance")
    l10n_ke_pension_allowance = fields.Monetary("Pension Allowance")

    l10n_ke_voluntary_medical_insurance = fields.Monetary("Voluntary medical Insurance")
    l10n_ke_life_insurance = fields.Monetary("Life Insurance")
    l10n_ke_is_li_managed_by_employee = fields.Boolean(
        string="Managed by Employee",
        help="If selected, Life Insurance will be paid by the employee on his own, only the life insurance relief will be deduced from payslip.")
    l10n_ke_education = fields.Monetary("Education")

    l10n_ke_is_secondary = fields.Boolean(
        string="Secondary Contract",
        help="Check if the employee got a main contract in another company.")
