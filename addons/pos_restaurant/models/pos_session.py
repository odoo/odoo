# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    @api.model
    def _load_pos_data_models(self, config):
        data = super()._load_pos_data_models(config)
        if self.config_id.module_pos_restaurant:
            data += ['restaurant.floor', 'restaurant.table', 'restaurant.order.course', 'pos.course']
        return data

    @api.model
    def _set_last_order_preparation_change(self, order_ids):
        for order_id in order_ids:
            self.env['pos.prep.order']._compute_prep_order(order_id)
