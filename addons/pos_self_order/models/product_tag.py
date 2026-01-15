# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import api, models


class ProductTag(models.Model):
    _inherit = 'product.tag'

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name == "image" and self.sudo().visible_to_customers:
            return True
        return super()._can_return_content(field_name, access_token)

    @api.model
    def _load_pos_self_data_domain(self, data, config):
        return [('visible_to_customers', '=', True)]
