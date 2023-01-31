# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class PurchaseRequisition(models.Model):
    _inherit = 'purchase.requisition'

    def _get_picking_in(self):
        pick_in = self.env.ref('stock.picking_type_in', raise_if_not_found=False)
        company = self.env.company
        if not pick_in or not pick_in.sudo().active or pick_in.sudo().warehouse_id.company_id.id != company.id:
            pick_in = self.env['stock.picking.type'].search(
                [('warehouse_id.company_id', '=', company.id), ('code', '=', 'incoming')],
                limit=1,
            )
        return pick_in

    warehouse_id = fields.Many2one('stock.warehouse', string='Warehouse', domain="[('company_id', '=', company_id)]")
    picking_type_id = fields.Many2one('stock.picking.type', 'Operation Type', required=True, default=_get_picking_in, domain="['|',('warehouse_id', '=', False), ('warehouse_id.company_id', '=', company_id)]")
    procurement_group_id = fields.Many2one('procurement.group', 'Procurement Group')

    def _prepare_tender_values(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        return {
            'origin': origin,
            'date_end': values['date_planned'],
            'user_id': False,
            'warehouse_id': values.get('warehouse_id') and values['warehouse_id'].id or False,
            'procurement_group_id': values.get('group_id') and values['group_id'].id or False,
            'company_id': company_id.id,
            'line_ids': [(0, 0, {
                'product_id': product_id.id,
                'product_uom_id': product_uom.id,
                'product_qty': product_qty,
                'product_description_variants': values.get('product_description_variants'),
                'move_dest_id': values.get('move_dest_ids') and values['move_dest_ids'][0].id or False
            })],
        }


class PurchaseRequisitionLine(models.Model):
    _inherit = "purchase.requisition.line"

    move_dest_id = fields.Many2one('stock.move', 'Downstream Move')

    def _prepare_purchase_order_line(self, name, product_qty=0.0, price_unit=0.0, taxes_ids=False):
        res = super(PurchaseRequisitionLine, self)._prepare_purchase_order_line(name, product_qty, price_unit, taxes_ids)
        res['move_dest_ids'] = self.move_dest_id and [(4, self.move_dest_id.id)] or []
        return res
