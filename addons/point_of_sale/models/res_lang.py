from odoo import models, api
from odoo.addons import point_of_sale, http_routing


class ResLang(http_routing.ResLang, point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['id', 'name', 'code', 'flag_image_url', 'display_name']
