# Copyright 2018 Aitor Bouzas <aitor.bouzas@adaptivecity.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class City(models.Model):
    _inherit = "res.city"

    zip_ids = fields.One2many("res.city.zip", "city_id", string="Zips in this city")

    _sql_constraints = [
        (
            "name_state_country_uniq",
            "UNIQUE(name, state_id, country_id)",
            "You already have a city with that name in the same state."
            "The city must have a unique name within "
            "it's state and it's country",
        )
    ]
