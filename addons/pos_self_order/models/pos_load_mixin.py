# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api
from odoo.addons import point_of_sale


class PosLoadMixin(point_of_sale.PosLoadMixin):

    @api.model
    def _load_pos_self_data_domain(self, data):
        return self._load_pos_data_domain(data)

    @api.model
    def _load_pos_self_data_fields(self, config_id):
        return self._load_pos_data_fields(config_id)

    def _load_pos_self_data(self, data):
        domain = self._load_pos_self_data_domain(data)
        fields = self._load_pos_self_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False),
            'fields': fields,
        }
