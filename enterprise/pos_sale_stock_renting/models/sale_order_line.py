# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class RentalOrderLine(models.Model):
    _inherit = 'sale.order.line'

    def _compute_qty_delivered(self):
        """This contains a duplicate of the sale_stock_renting and pos_sale logic.
           This is required because the value written in pos_sale would be overwritten
           by the sale_stock_renting logic. Doing this here make sure that the PoS value
           is no erased because it's the last one written.
        """
        super()._compute_qty_delivered()

        if not self.with_context(skip_pos_rental_pickings_check=True)._are_rental_pickings_enabled():
            return

        for line in self:
            if line.is_rental:
                qty = 0.0
                outgoing_moves, _ = line.with_context(skip_pos_rental_pickings_check=True)._get_outgoing_incoming_moves()
                for move in outgoing_moves:
                    if move.state != 'done':
                        continue
                    qty += move.product_uom._compute_quantity(move.quantity, line.product_uom, rounding_method='HALF-UP')
                line.qty_delivered = qty
                if all(picking.state == 'done' for picking in line.pos_order_line_ids.order_id.picking_ids):
                    line.qty_delivered += sum((self._convert_qty(line, pos_line.qty, 'p2s') for pos_line in line.pos_order_line_ids if line.product_id.type != 'service'), 0)

    def _are_rental_pickings_enabled(self):
        if super()._are_rental_pickings_enabled():
            return True
        if not self.env.context.get('skip_pos_rental_pickings_check'):
            return False
        return any(line.pos_order_line_ids for line in self)
