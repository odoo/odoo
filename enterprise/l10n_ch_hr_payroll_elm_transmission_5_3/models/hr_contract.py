# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class HrContract(models.Model):
    _inherit = 'hr.contract'

    l10n_ch_lpp_in_percentage = fields.Boolean(
        string="LPP Contributions in Percentage",
        default=False,
        help="If checked, LPP contributions are specified as percentages instead of fixed amounts.",
        groups="hr_payroll.group_hr_payroll_user"
    )
    l10n_ch_lpp_percentage_employee = fields.Float(
        string="Employee LPP Contribution (%)",
        digits='Payroll Rate',
        groups="hr_payroll.group_hr_payroll_user"
    )
    l10n_ch_lpp_percentage_employer = fields.Float(
        string="Employer LPP Contribution (%)",
        digits='Payroll Rate',
        groups="hr_payroll.group_hr_payroll_user"
    )
    #When engaging in gainful activity at the reference age, it is now possible to waive the exemption.
    #This waiver allows for filling contribution gaps and, in general, improving AVS pensions up to the maximum pension.
    #The waiver is generally only meaningful until the end of the month in which the insured reaches the age of 70 (reference age + 5 years),
    #as income earned after age 70 no longer contributes to pensions.
    #The worker must inform their employer, before the first salary payment of the year or the first salary payment after reaching the reference age,
    #that they do not wish to use the exemption. Without notification, the exemption is automatically deducted.
    #The worker's choice is valid for the entire year and is automatically carried over to the following year,
    #unless the employer is notified otherwise before the first salary payment of the subsequent year.

    l10n_ch_avs_status = fields.Selection(selection_add=[
        ('retired_wave_deduct', "Retired with Waive of Pension Deduct")
    ])
