# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def _default_picking_type_id(self):
        return self.env['stock.picking.type'].search([('warehouse_id.company_id', '=', self.env.company.id), ('code', '=', 'incoming')], limit=1)

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', domain="[('company_id', '=', company_id)]")
    picking_type_id = fields.Many2one(
        'stock.picking.type', 'Operation Type', required=True, default=_default_picking_type_id,
        domain="['|',('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]")


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    move_dest_id = fields.Many2one('stock.move', 'Downstream Move')

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        res = super(PurchaseRequisitionLine, self)._prepare_purchase_order_line(name, product_qty, price_unit, taxes_ids)
        res['move_dest_ids'] = self.move_dest_id and [(4, self.move_dest_id.id)] or []
        return res
