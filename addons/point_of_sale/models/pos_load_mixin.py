# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import models, api


class PosLoadMixin(models.AbstractModel):
    _name = "pos.load.mixin"
    _description = "PoS data loading mixin"

    @api.model
    def _load_pos_data_fields(self, config_id):
        return []

    @api.model
    def _load_pos_data_domain(self, data):
        return []

    # If you need to adapt the data to be loaded in the PoS, you can
    # override this method in your model.
    def _load_pos_data(self, data):
        domain = self._load_pos_data_domain(data)
        fields = self._load_pos_data_fields(data['pos.config']['data'][0]['id'])
        return {
            'data': self.search_read(domain, fields, load=False) if domain is not False else [],
            'fields': fields,
        }
