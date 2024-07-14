# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipInput(models.Model):
    _inherit = "hr.payslip.input.type"

    l10n_au_default_amount = fields.Float(
        string="Default Amount",
        help="Default amount for this input type")
    l10n_au_is_allowance = fields.Boolean(string="Is Allowance")
    l10n_au_allowance_type = fields.Selection(
        selection=[
            ('service', 'Services'),
            ('expense_ded', 'Deductible Expenses'),
            ('expense_nonded', 'Non-Deductible Expenses')],
        string="Allowance Type",
        default='service')
    l10n_au_is_etp = fields.Boolean(string="Is ETP")
    l10n_au_etp_type = fields.Selection(
        selection=[
            ('excluded', 'Excluded'),
            ('non_excluded', 'Non-Excluded')],
        string="ETP Type")
    l10n_au_etp_cap = fields.Boolean(string="ETP Cap")
