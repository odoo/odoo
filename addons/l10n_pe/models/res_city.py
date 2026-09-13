from odoo import fields, models


class ResCity(models.Model):
    _inherit = "res.city"

    l10n_pe_code = fields.Char(
        string="Code",
        help="This code will help with the identification of each city in Peru.",
    )
