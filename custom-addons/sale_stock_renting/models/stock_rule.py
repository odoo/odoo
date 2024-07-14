# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class StockRule(models.Model):
    _inherit = 'stock.rule'

    def _push_prepare_move_copy_values(self, move_to_copy, new_date):
        """ Set the dates of rental return pickings based on the return date of the rental order.
        Set the product_uom_qty of the return move according to the existing moves to avoid discrepancies. """
        new_move_vals = super()._push_prepare_move_copy_values(move_to_copy, new_date)
        if move_to_copy.sale_line_id.is_rental and self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            return_quantity = 0.0
            if move_to_copy.location_dest_id == move_to_copy.company_id.rental_loc_id:
                for move in move_to_copy.sale_line_id.move_ids:
                    if move._should_ignore_rented_qty(move_to_copy):
                        continue
                    if move.location_dest_id == move.company_id.rental_loc_id:
                        return_quantity += move.product_uom._compute_quantity(move.product_qty, move_to_copy.sale_line_id.product_uom, rounding_method='HALF-UP')
                    else:
                        return_quantity -= move.product_uom._compute_quantity(move.product_qty, move_to_copy.sale_line_id.product_uom, rounding_method='HALF-UP')
            new_move_vals.update({
                'date': move_to_copy.sale_line_id.return_date,
                'date_deadline': move_to_copy.sale_line_id.return_date,
                'product_uom_qty': return_quantity or move_to_copy.product_qty,
                'origin_returned_move_id': move_to_copy.id
            })
        return new_move_vals
