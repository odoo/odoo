# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class PosConfig(models.Model):
    _inherit = 'pos.config'

    def get_limited_products_loading(self, fields):
        result = super().get_limited_products_loading(fields)
        current_session = self.current_session_id
        ticket_product_ids = list(map(lambda ticket: ticket['product_id'][0], current_session._get_pos_ui_event_event_ticket(current_session._loader_params_event_event_ticket())))
        event_products = self.env['product.product'].search_read([('id', 'in', ticket_product_ids)], fields=fields)
        return result+event_products
