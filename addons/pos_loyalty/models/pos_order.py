# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models


class PosOrder(models.Model):
    _inherit = 'pos.order'

    loyalty_points = fields.Float(help='The amount of Loyalty points the customer won or lost with this order')

    @api.model
    def _order_fields(self, ui_order):
        fields = super(PosOrder, self)._order_fields(ui_order)
        fields['loyalty_points'] = ui_order.get('loyalty_points', 0)
        return fields

    @api.model
    def create_from_ui(self, orders):
        order_ids = super(PosOrder, self).create_from_ui(orders)
        for order in orders:
            if order['data']['loyalty_points'] != 0 and order['data']['partner_id']:
                partner = self.env['res.partner'].browse(order['data']['partner_id'])
                partner.write({'loyalty_points': partner['loyalty_points'] + order['data']['loyalty_points']})
        return order_ids
