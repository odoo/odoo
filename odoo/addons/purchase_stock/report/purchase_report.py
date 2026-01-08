# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseReport(models.Model):
    _inherit = "purchase.report"

    picking_type_id = fields.Many2one('stock.warehouse', 'Warehouse', readonly=True)
    effective_date = fields.Datetime(string="Effective Date")

    def _select(self):
        return super(PurchaseReport, self)._select() + ", spt.warehouse_id as picking_type_id, po.effective_date as effective_date"

    def _from(self):
        return super(PurchaseReport, self)._from() + " left join stock_picking_type spt on (spt.id=po.picking_type_id)"

    def _group_by(self):
        return super(PurchaseReport, self)._group_by() + ", spt.warehouse_id, effective_date"
