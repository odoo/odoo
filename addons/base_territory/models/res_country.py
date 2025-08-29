# Copyright (C) 2020 Open Source Integrators
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import fields, models


class ResCountry(models.Model):
    _inherit = "res.country"

    territory_id = fields.Many2one("res.territory", string="Territory")
    region_ids = fields.Many2many(
        "res.region",
        "res_country_region_rel",
        "country_id",
        "region_id",
        string="Regions",
    )
