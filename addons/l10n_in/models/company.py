from odoo import fields, models, _

class ResCompany(models.Model):
    _inherit = 'res.company'

    l10n_in_upi_id = fields.Char(string="UPI Id")
    l10n_in_hsn_code_digit = fields.Selection(
        selection=[
            ("4", "4 Digits"),
            ("6", "6 Digits"),
            ("8", "8 Digits"),
        ],
        string="HSN Code Digit",
    )
