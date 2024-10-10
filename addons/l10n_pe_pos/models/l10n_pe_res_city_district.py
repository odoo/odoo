# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api


class L10n_PeResCityDistrict(models.Model):
    _inherit = ["l10n_pe.res.city.district", "pos.load.mixin"]

    country_id = fields.Many2one(related="city_id.country_id")
    state_id = fields.Many2one(related="city_id.state_id")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["name", "city_id", "country_id", "state_id"]
