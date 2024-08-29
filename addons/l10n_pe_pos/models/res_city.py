# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons import base_address_extended, point_of_sale
from odoo import api, models


class ResCity(models.Model, base_address_extended.ResCity, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ["name", "country_id", "state_id"]
