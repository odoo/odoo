
from odoo import models
from odoo.tools.float_utils import float_compare


class StockMove(models.Model):
    _inherit = 'stock.move'

    def split_uncompleted_moves(self):
        """ Creates a new move for every uncompleted move in order to get one picked move
        with the picked quantity, and one not picked move with the remaining quantity."""
        # Backport of `stock.move` `_create_backorder` method. For more details, see
        # https://github.com/odoo/odoo/commit/7472d5546580f28d58abfd20774b6e3eedc9f29a
        # Split moves where necessary and move quants
        new_moves_vals = []
        for move in self:
            if not move.picked:
                continue
            # To know whether we need to split a move, rounds to the general
            # product's decimal precision and not the product's UOM.
            rounding = self.env['decimal.precision'].precision_get('Product Unit of Measure')
            if float_compare(move.quantity, move.product_uom_qty, precision_digits=rounding) < 0:
                # Need to do some kind of conversion here
                qty_split = move.product_uom._compute_quantity(
                    move.product_uom_qty - move.quantity,
                    move.product_id.uom_id,
                    rounding_method='HALF-UP')
                new_move_vals = move._split(qty_split)
                new_moves_vals += new_move_vals
        new_moves = self.env['stock.move'].create(new_moves_vals)
        # The new moves are not yet in their own picking. We do not want to check entire packs for those
        # ones as it could messed up the result_package_id of the moves being currently validated
        new_moves.with_context(bypass_entire_pack=True)._action_confirm(merge=False)
        if new_moves:
            # In some case, we already split the move lines in the front end.
            # Those move lines are linked to the original move. If their quantity
            # is 0 and they are already picked, there is no reason to keep them.
            moves_to_clean = self - new_moves
            move_lines_to_unlink = self.env['stock.move.line']
            for move in moves_to_clean:
                for move_line in move.move_line_ids:
                    if move_line.quantity == 0 and move_line.picked:
                        move_lines_to_unlink |= move_line
            move_lines_to_unlink.unlink()
        return new_moves
