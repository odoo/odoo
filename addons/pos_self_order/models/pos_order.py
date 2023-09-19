# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Dict

from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    combo_parent_id = fields.Many2one('pos.order.line', string='Combo Parent')
    combo_line_ids = fields.One2many('pos.order.line', 'combo_parent_id', string='Combo Lines')
    combo_id = fields.Many2one('pos.combo', string='Combo line reference')

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

    def _export_for_ui(self, orderline):
        return {
            'note': orderline.note,
            **super()._export_for_ui(orderline),
        }

class PosOrder(models.Model):
    _inherit = "pos.order"

    tracking_number = fields.Char(string="Tracking Number")
    take_away = fields.Boolean(string="Take Away", default=False)

    @api.model
    def create_from_ui(self, orders, draft=False):
        orders = super().create_from_ui(orders, draft)
        order_ids = self.env['pos.order'].browse([order['id'] for order in orders])

        if self.env.context.get('from_self') is not True:
            self._send_notification(order_ids)

        return orders

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)

        return super().remove_from_ui(server_ids)

    def _order_fields(self, ui_order):
        fields = super()._order_fields(ui_order)
        fields.update({
            'tracking_number': ui_order.get('tracking_number'),
            'take_away': ui_order.get('take_away'),
        })
        return fields

    def _send_notification(self, order_ids):
        for order in order_ids:
            if order.access_token and order.state != 'draft':
                self.env['bus.bus']._sendone(f'self_order-{order.access_token}', 'ORDER_STATE_CHANGED', {
                    'access_token': order.access_token,
                    'state': order.state
                })
            else:
                self.env['bus.bus']._sendone(f'self_order-{order.access_token}', 'ORDER_CHANGED', {
                    'order': order._export_for_self_order()
                })

    def _export_for_self_order(self) -> Dict:
        self.ensure_one()

        return {
            "id": self.id,
            "pos_config_id": self.config_id.id,
            "take_away": self.take_away,
            "pos_reference": self.pos_reference,
            "access_token": self.access_token,
            "tracking_number": self.tracking_number,
            "state": self.state,
            "date_order": str(self.date_order),
            "amount_total": self.amount_total,
            "amount_tax": self.amount_tax,
            "lines": [
                {
                    "id": line.id,
                    "price_subtotal": line.price_subtotal,
                    "price_subtotal_incl": line.price_subtotal_incl,
                    "product_id": line.product_id.id,
                    "selected_attributes": line.attribute_value_ids.ids,
                    "uuid": line.uuid,
                    "qty": line.qty,
                    "customer_note": line.customer_note,
                    "full_product_name": line.full_product_name,
                }
                for line in self.lines
            ],
        }
