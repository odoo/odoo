from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    enforce_cities = fields.Boolean(
        help="Check this box to ensure every address created in that country has a 'City' chosen "
        "in the list of the country's cities."
    )
