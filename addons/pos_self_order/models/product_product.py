# Part of Odoo. See LICENSE file for full copyright and licensing details.
from __future__ import annotations

from odoo import models


class ProductProduct(models.Model):
    _inherit = "product.product"

    def write(self, vals):
        res = super().write(vals)
        if 'self_order_available' in vals:
            for record in self:
                record._send_availability_status()
        return res

    def _send_availability_status(self):
        config_self = self.env['pos.config'].sudo().search([('self_ordering_mode', '!=', 'nothing')])
        for config in config_self:
            if config.access_token and config.current_session_id:
                records = self.env["product.template"].load_product_from_pos(config.id, [('id', '=', self.product_tmpl_id.id)])
                payload = {}
                self_models = self.env["pos.config"]._load_self_data_models()
                for model in records:
                    if model in self_models:
                        payload[model] = records[model]
                config._notify('PRODUCT_CHANGED', payload)

    def _can_return_content(self, field_name=None, access_token=None):
        if field_name == "image_512" and self.sudo().self_order_available:
            return True
        return super()._can_return_content(field_name, access_token)
