# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    on_time_rate_perc = fields.Float(string="OTD", compute="_compute_on_time_rate_perc")

    @api.depends('on_time_rate')
    def _compute_on_time_rate_perc(self):
        for po in self:
            if po.on_time_rate >= 0:
                po.on_time_rate_perc = po.on_time_rate / 100
            else:
                po.on_time_rate_perc = -1

    @api.onchange('requisition_id')
    def _onchange_requisition_id(self):
        super(PurchaseOrder, self)._onchange_requisition_id()
        if self.requisition_id:
            self.picking_type_id = self.requisition_id.picking_type_id.id


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    on_time_rate_perc = fields.Float(string="OTD", related="order_id.on_time_rate_perc")
