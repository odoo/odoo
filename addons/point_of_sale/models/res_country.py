from odoo import models, api
from odoo.addons import point_of_sale, base


class ResCountry(base.ResCountry, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'code', 'vat_label']
