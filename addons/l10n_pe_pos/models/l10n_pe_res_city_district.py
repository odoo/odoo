# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import l10n_pe, point_of_sale
from odoo import fields, models, api


class L10nPeResCityDistrict(models.Model, l10n_pe.L10nPeResCityDistrict, point_of_sale.PosLoadMixin):
    _name = "l10n_pe.res.city.district"

    country_id = fields.Many2one(related="city_id.country_id")
    state_id = fields.Many2one(related="city_id.state_id")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["name", "city_id", "country_id", "state_id"]
