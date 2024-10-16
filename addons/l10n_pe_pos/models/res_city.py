# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models
from odoo.addons import point_of_sale, l10n_pe


class ResCity(l10n_pe.ResCity, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["name", "country_id", "state_id"]
