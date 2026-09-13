from odoo import fields, models


class L10n_PeResCityDistrict(models.Model):
    _name = "l10n_pe.res.city.district"
    _description = "District"
    _order = "name"

    name = fields.Char(translate=True)
    city_id = fields.Many2one(comodel_name="res.city")
    code = fields.Char(
        help="This code will help with the identification of each district in Peru."
    )
