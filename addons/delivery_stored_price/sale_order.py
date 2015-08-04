# -*- coding: utf-8 -*-
from openerp import models, fields, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    delivery_price = fields.Float(compute='_compute_delivery_price_stored', store=True)

    @api.depends('carrier_id', 'partner_id', 'order_line')
    def _compute_delivery_price_stored(self):
        for order in self:
            if order.state != 'draft':
                # we do not want to recompute the shipping price of an already validated/done SO
                continue
            elif order.carrier_id.delivery_type != 'grid' and not order.order_line:
                # prevent SOAP call to external shipping provider when SO has no lines yet
                continue
            else:
                order.delivery_price = order.carrier_id.with_context(order_id=order.id).price
