# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _should_ignore_rented_qty(self, sibling):
        self.ensure_one()
        sibling.ensure_one()
        return self.state == 'cancel' or self.product_id != sibling.product_id or self.scrapped or self.picking_code not in ('outgoing', 'incoming')

    def _search_picking_for_assignation_domain(self):
        """ This modifies the picking search domain for rental moves.

        Modify the picking search domain to make sure that rental moves are on the
        same picking as sale moves in case of hybrid rental orders, while still making
        sure that modifying the SO line quantity is propagated to stock moves correctly.
        """
        domain = super()._search_picking_for_assignation_domain()
        rental_loc = self.company_id.rental_loc_id
        if (self.env.user.has_group('sale_stock_renting.group_rental_stock_picking') and rental_loc
                and self.sale_line_id and self.sale_line_id.order_id.is_rental_order
                and self.location_dest_id.id in (rental_loc.id, rental_loc.location_id.id)):
            index_to_insert = domain.index(('location_dest_id', '=', self.location_dest_id.id))
            domain.pop(index_to_insert)
            domain.insert(index_to_insert, ('location_dest_id', '=', rental_loc.id))
            domain.insert(index_to_insert, ('location_dest_id', '=', rental_loc.location_id.id))
            domain.insert(index_to_insert, '|')
        return domain

    @api.model
    def _prepare_merge_moves_distinct_fields(self):
        distinct_fields = super()._prepare_merge_moves_distinct_fields()
        if any(sale_order.is_rental_order for sale_order in self.group_id.sale_id):
            distinct_fields.remove('origin_returned_move_id')
        return distinct_fields

    def _action_assign(self, force_qty=False):
        """ Assign the lot_id present on the SO line to the stock move lines for rental orders. """
        super()._action_assign(force_qty=force_qty)

        for product in self.product_id:
            if not product.tracking == 'serial':
                continue
            moves = self.filtered(lambda m: m.product_id == product)
            sale_lines = self.env['sale.order.line']
            for move in moves:
                sale_lines |= move._get_sale_order_lines()
            if sale_lines.reserved_lot_ids:
                free_reserved_lots = sale_lines.reserved_lot_ids.filtered(lambda s: s not in moves.move_line_ids.lot_id)
                to_assign_move_lines = moves.move_line_ids.filtered(lambda l: l.lot_id not in sale_lines.reserved_lot_ids)
                for line, lot in zip(to_assign_move_lines, free_reserved_lots):
                    quant = lot.quant_ids.filtered(lambda q: q.location_id == line.location_id and q.quantity == 1 and q.reserved_quantity == 0)
                    if quant:
                        line.lot_id = lot

    def _action_done(self, cancel_backorder=False):
        """ Correctly set the qty_delivered and qty_returned of rental order lines when using pickings."""
        res = super()._action_done(cancel_backorder=cancel_backorder)
        if self.env.user.has_group('sale_stock_renting.group_rental_stock_picking'):
            for move in self:
                if move.state != "done":
                    continue
                if not move.sale_line_id.is_rental or move.product_id != move.sale_line_id.product_id:
                    continue
                if move.location_id == move.company_id.rental_loc_id:
                    current_qty_returned = move.product_uom._compute_quantity(move.quantity, move.sale_line_id.product_uom, rounding_method='HALF-UP')
                    if move.sale_line_id.order_id.is_late:
                        move.sale_line_id._generate_delay_line(current_qty_returned)
                    move.sale_line_id.qty_returned += current_qty_returned
        return res
