# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import fields, models, api
from odoo.addons import point_of_sale, l10n_pe


class L10n_PeResCityDistrict(l10n_pe.L10n_PeResCityDistrict, point_of_sale.PosLoadMixin):

    country_id = fields.Many2one(related="city_id.country_id")
    state_id = fields.Many2one(related="city_id.state_id")

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["name", "city_id", "country_id", "state_id"]
