# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    combo_id = fields.Many2one('product.combo', string='Combo reference')

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if (vals.get('combo_parent_uuid')):
                vals.update([
                    ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
                ])
            if 'combo_parent_uuid' in vals:
                del vals['combo_parent_uuid']
        return super().create(vals_list)

    def write(self, vals):
        if (vals.get('combo_parent_uuid')):
            vals.update([
                ('combo_parent_id', self.search([('uuid', '=', vals.get('combo_parent_uuid'))]).id)
            ])
        if 'combo_parent_uuid' in vals:
            del vals['combo_parent_uuid']
        return super().write(vals)

class PosOrder(models.Model):
    _inherit = "pos.order"

    table_stand_number = fields.Char(string="Table Stand Number")

    @api.model
    def _load_pos_self_data_domain(self, data):
        return [('id', '=', False)]

    @api.model
    def sync_from_ui(self, orders):
        for order in orders:
            if order.get('id'):
                order_id = order['id']

                if isinstance(order_id, int):
                    old_order = self.env['pos.order'].browse(order_id)
                    if old_order.takeaway:
                        order['takeaway'] = old_order.takeaway

        result = super().sync_from_ui(orders)
        order_ids = self.browse([order['id'] for order in result['pos.order'] if order.get('id')])
        self._send_notification(order_ids)
        return result

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)
        return super().remove_from_ui(server_ids)

    def _send_notification(self, order_ids):
        config_ids = order_ids.config_id
        for config in config_ids:
            config._notify('ORDER_STATE_CHANGED', {})
