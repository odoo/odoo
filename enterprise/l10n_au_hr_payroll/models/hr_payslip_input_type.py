# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class HrPayslipInput(models.Model):
    _inherit = "hr.payslip.input.type"
    _order = "l10n_au_payment_type"
    currency_id = fields.Many2one(
        "res.currency", string="Currency",
        default=lambda self: self.env.company.currency_id,
    )
    l10n_au_default_amount = fields.Monetary(
        string="Default Amount", currency_field="currency_id",
        help="Default amount for this input type")
    l10n_au_etp_type = fields.Selection(
        selection=[
            ('excluded', 'Excluded'),
            ('non_excluded', 'Non-Excluded')],
        string="ETP Type")

    l10n_au_payment_type = fields.Selection(
        selection=[
            ("etp", "ETP"),
            ("allowance", "Allowance"),
            ("lump_sum", "Lump Sum"),
            ("deduction", "Deduction"),
            ("leave", "Leave"),
            ("other", "Other"),
        ],
        string="Payment Type",
    )

    l10n_au_superannuation_treatment = fields.Selection(
        selection=[
            ("ote", "OTE"),
            ("salary", "Salary & Wages"),
            ("not_salary", "Not Salary & Wages"),
        ],
        string="Superannuation Treatment",
    )

    l10n_au_paygw_treatment = fields.Selection(
        [('regular', 'Regular'),
        ('no_paygw', 'No PAYG Withholding'),
        ('excess', 'Excess Only'),
        ],
        string="PAYGW Treatment",
    )

    l10n_au_payroll_code = fields.Char(string="STP Code")
    l10n_au_payroll_code_description = fields.Selection(
        selection=[
            ('G1', 'G1'),
            ('H1', 'H1'),
            ('ND', 'ND'),
            ('T1', 'T1'),
            ('U1', 'U1'),
            ('V1', 'V1'),
        ],
        string="Payroll Code Description",
    )

    l10n_au_ato_rate_limit = fields.Float(string="ATO Rate Limit")
