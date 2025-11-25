# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models, fields
from odoo.fields import Command


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    dropship_picking_count = fields.Integer("Dropship Count", compute='_compute_incoming_picking_count')

    @api.depends('picking_ids.is_dropship')
    def _compute_incoming_picking_count(self):
        super()._compute_incoming_picking_count()
        for order in self:
            dropship_count = len(order.picking_ids.filtered(lambda p: p.is_dropship))
            order.incoming_picking_count -= dropship_count
            order.dropship_picking_count = dropship_count

    def action_view_picking(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda p: not p.is_dropship))

    def action_view_dropship(self):
        return self._get_action_view_picking(self.picking_ids.filtered(lambda p: p.is_dropship))

    def _prepare_reference_vals(self):
        res = super()._prepare_reference_vals()
        sale_orders = self.order_line.sale_order_id
        if len(sale_orders) == 1:
            res['sale_ids'] = [Command.link(sale_orders.id)]
        return res

    def _is_dropshipped(self):
        self.ensure_one()
        return self.picking_type_id and self.picking_type_id.code == 'dropship'


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _is_dropshipped(self):
        return self.order_id._is_dropshipped()
