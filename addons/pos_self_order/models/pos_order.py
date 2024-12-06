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

<<<<<<< saas-18.1
||||||| ee48df7f33a3aeb1798bf5852be8c6d26a7db7fd
    @api.model
    def sync_from_ui(self, orders):
        for order in orders:
            if order.get('id'):
                order_id = order['id']

                if isinstance(order_id, int):
                    old_order = self.env['pos.order'].browse(order_id)
                    if old_order.takeaway:
                        order['takeaway'] = old_order.takeaway

        return super().sync_from_ui(orders)

=======
    @api.model
    def sync_from_ui(self, orders):
        for order in orders:
            if order.get('id'):
                order_id = order['id']

                if isinstance(order_id, int):
                    old_order = self.env['pos.order'].browse(order_id)
                    if old_order.takeaway:
                        order['takeaway'] = old_order.takeaway

        return super().sync_from_ui(orders)

    def _get_open_order(self, order):
        open_order = super()._get_open_order(order)
        if not self.env.context.get('from_self'):
            return open_order
        elif open_order:
            del order['table_id']
        return self.env['pos.order'].search([('uuid', '=', order.get('uuid'))], limit=1)

>>>>>>> 97299e0514367ceefbf007d85db1a68e4448c4d2
    def _process_saved_order(self, draft):
        res = super()._process_saved_order(draft)

        if self.env.context.get('from_self') is not True:
            self._send_notification(self)

        return res

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)
        return super().remove_from_ui(server_ids)

    def _send_notification(self, order_ids):
        for order in order_ids:
            order._notify('ORDER_STATE_CHANGED', {
                'pos.order': order.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
                'pos.order.line': order.lines.read(order._load_pos_self_data_fields(order.config_id.id), load=False),
                'pos.payment': order.payment_ids.read(order.payment_ids._load_pos_data_fields(order.config_id.id), load=False),
                'pos.payment.method': order.payment_ids.mapped('payment_method_id').read(self.env['pos.payment.method']._load_pos_data_fields(order.config_id.id), load=False),
                'product.attribute.custom.value':  order.lines.custom_attribute_value_ids.read(order.lines.custom_attribute_value_ids._load_pos_data_fields(order.config_id.id), load=False),
            })
