from odoo import models


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _load_pos_self_metadata(self, data, search_params={}):
        super()._load_pos_self_metadata(data, search_params)
        old_data = data['product.template']
        self._load_pos_metadata(data, search_params)
        data['product.template'] = {
            **old_data,
            'records': data['product.template']['records']
        }
        return data
