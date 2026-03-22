from odoo import fields, models


class ResCountryState(models.Model):
    _inherit = "res.country.state"

    br_ibge_code = fields.Char(
        string="Codigo IBGE",
        size=2,
        help="Codigo IBGE da unidade federativa.",
    )

