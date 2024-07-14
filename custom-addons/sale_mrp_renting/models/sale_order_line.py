# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _get_qty_procurement(self, previous_product_uom_qty=False):
        qty = super()._get_qty_procurement(previous_product_uom_qty)
        if self.is_rental and self.env.user.has_group('sale_stock_renting.group_rental_stock_picking') and 'phantom' in self.product_id.bom_ids.mapped('type'):
            bom = self.env['mrp.bom']._bom_find(self.product_id, bom_type='phantom')[self.product_id]
            outgoing_moves = self.move_ids.filtered(lambda m: m.location_dest_id == m.company_id.rental_loc_id and m.state != 'cancel' and not m.scrapped and m.product_id in bom.bom_line_ids.product_id)
            filters = {
                'incoming_moves': lambda m: m.location_dest_id == m.company_id.rental_loc_id and (not m.origin_returned_move_id or (m.origin_returned_move_id and m.to_refund)),
                'outgoing_moves': lambda m: m.location_dest_id != m.company_id.rental_loc_id and m.to_refund
            }
            order_qty = previous_product_uom_qty.get(self.id, 0) if previous_product_uom_qty else self.product_uom_qty
            order_qty = self.product_uom._compute_quantity(order_qty, bom.product_uom_id)
            qty_to_compute = outgoing_moves._compute_kit_quantities(self.product_id, order_qty, bom, filters)
            qty = bom.product_uom_id._compute_quantity(qty_to_compute, self.product_uom)
        return qty
