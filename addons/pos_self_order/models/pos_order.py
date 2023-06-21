# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from typing import Dict

from odoo import models, fields, api


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    # For the moment we need this to keep attributes consistency between the server and client_side.
    selected_attributes = fields.Json(string="Selected Attributes")

    # FIXME: uuid already pass in pos and move note in pos_restaurant.
    def _export_for_ui(self, orderline):
        return {
            'uuid': orderline.uuid,
            'note': orderline.note,
            **super()._export_for_ui(orderline),
        }


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model
    def create_from_ui(self, orders, draft=False):
        orders = super().create_from_ui(orders, draft)
        order_ids = self.env['pos.order'].browse([order['id'] for order in orders])
        self._send_notification(order_ids)
        return orders

    @api.model
    def remove_from_ui(self, server_ids):
        order_ids = self.env['pos.order'].browse(server_ids)
        order_ids.state = 'cancel'
        self._send_notification(order_ids)

        return super().remove_from_ui(server_ids)

    def _send_notification(self, order_ids):
        for order in order_ids:
            if order.access_token and order.state != 'draft':
                self.env['bus.bus']._sendone(f'self_order-{order.access_token}', 'ORDER_STATE_CHANGED', {
                    'access_token': order.access_token,
                    'state': order.state
                })

    def _export_for_self_order(self) -> Dict:
        self.ensure_one()

        return {
            "id": self.id,
            "pos_config_id": self.config_id.id,
            "pos_reference": self.pos_reference,
            "access_token": self.access_token,
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
                    "selected_attributes": line.selected_attributes,
                    "uuid": line.uuid,
                    "qty": line.qty,
                    "customer_note": line.customer_note,
                    "full_product_name": line.full_product_name,
                }
                for line in self.lines
            ],
        }
