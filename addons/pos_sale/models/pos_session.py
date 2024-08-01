# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api


class PosSession(models.Model):
    _inherit = 'pos.session'

    crm_team_id = fields.Many2one('crm.team', related='config_id.crm_team_id', string="Sales Team", readonly=True)

    @api.model
    def _load_pos_data_models(self, config_id):
        data = super()._load_pos_data_models(config_id)
        data += ['sale.order', 'sale.order.line']
        return data

    def _load_pos_data(self, data):
        data = super()._load_pos_data(data)
        data['data'][0]['_sale_order_tree_view_id'] = self.env.ref('pos_sale.view_order_tree_inherit_pos_sale').id
        data['data'][0]['_sale_order_kanban_view_id'] = self.env.ref('pos_sale.view_order_kanban_inherit_pos_sale').id
        return data
