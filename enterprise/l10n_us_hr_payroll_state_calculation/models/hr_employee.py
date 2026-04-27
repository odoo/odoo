# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = "hr.employee"

    l10n_us_state_withholding_allowance = fields.Float(
        string="State Withholding Allowance",
        groups="hr.group_hr_user",
        help="Add the allowance the employee wants to deduct from their State's withholding (usually an annual amount) "
             "according to their State Withholding Certificate. If the employee didn't fill out a State Withholding "
             "Certificate, leave it blank")
    l10n_us_state_extra_withholding = fields.Float(
        string="State Extra Withholding",
        groups="hr.group_hr_user",
        help="Extra amount the employee requests to be withheld per pay period according to their State Withholding "
             "Certificate. If the employee didn't fill out a State Withholding Certificate, leave it blank.")
