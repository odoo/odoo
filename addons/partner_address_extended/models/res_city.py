from odoo import api, fields, models

from odoo.addons.base.models.mixin_catalog import name_uniq_index


class ResCity(models.Model):
    _name = "res.city"
    _description = "City"
    _order = "name"
    _rec_names_search = ["name", "zipcode"]

    name = fields.Char(
        translate=True,
        required=True,
    )
    zipcode = fields.Char(string="Zip")
    country_id = fields.Many2one(
        comodel_name="res.country",
        required=True,
    )
    state_id = fields.Many2one(
        comodel_name="res.country.state",
        domain="[('country_id', '=', country_id)]",
    )

    _name_zipcode_state_country_uniq = name_uniq_index(
        "zipcode",
        "state_id",
        "country_id",
        message="A city with this name, zip code, state and country already exists.",
    )

    @api.depends("zipcode")
    def _compute_display_name(self):
        for city in self:
            name = city.name if not city.zipcode else f"{city.name} ({city.zipcode})"
            city.display_name = name
