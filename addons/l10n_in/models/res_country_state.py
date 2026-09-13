from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    l10n_in_tin = fields.Char(
        string="TIN Number",
        help="TIN number-first two digits",
        size=2,
    )
