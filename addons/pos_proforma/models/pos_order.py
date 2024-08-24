# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api


class PosOrder(models.Model):
    _inherit = 'pos.order'

    receipt_type = fields.Char(readonly=True)

    @api.model
    def create_from_ui(self, orders, draft=False):
        pro_forma_orders = [order['data'] for order in orders if order['data'].get('receipt_type') == "PS"]
        regular_orders = [order for order in orders if not order['data'].get('receipt_type') == "PS"]
        self.env['pos.order_pro_forma'].create_from_ui(pro_forma_orders)
        return super(PosOrder, self).create_from_ui(regular_orders, draft)

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['receipt_type'] = ui_order.get('receipt_type', False)
        return order_fields

    def _export_for_ui(self, order):
        result = super(PosOrder, self)._export_for_ui(order)
        result['receipt_type'] = order.receipt_type
        return result
