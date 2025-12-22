# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, fields, api


class ResCity(models.Model):
    _inherit = "res.city"

    l10n_br_zip_range_ids = fields.One2many(
        string="Zip Ranges",
        comodel_name="l10n_br.zip.range",
        inverse_name="city_id",
        help="Brazil: technical field that maps a city to one or more zip code ranges.",
    )

    l10n_br_zip_ranges = fields.Char(
        string="Frontend Zip Ranges",
        compute="_compute_l10n_br_zip_ranges",
        help="Brazil: technical field that maps a city to one or more zip code ranges for the frontend.",
    )

    @api.depends("l10n_br_zip_range_ids")
    def _compute_l10n_br_zip_ranges(self):
        for city in self:
            city.l10n_br_zip_ranges = " ".join(
                city.l10n_br_zip_range_ids.mapped(lambda zip_range: f"[{zip_range.start} {zip_range.end}]")
            )
