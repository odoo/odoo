from odoo import models, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def create(self, vals):
        picking_type_id = vals.get('picking_type_id')
        picking_type = self.env['stock.picking.type'].browse(picking_type_id) if picking_type_id else None
        if (
            picking_type and
            picking_type.picking_process_type == 'returns' and
            vals.get('move_ids_without_package')
        ):
            new_moves = []
            for move in vals['move_ids_without_package']:
                if isinstance(move, (list, tuple)) and move[0] == 0:
                    move_data = dict(move[2])
                    qty = int(move_data.get('product_uom_qty', 1))
                    for i in range(qty):
                        single_move = move_data.copy()
                        single_move['product_uom_qty'] = 1
                        single_move['name'] = (move_data.get('name') or '') + f" (Return #{i+1})"
                        new_moves.append((0, 0, single_move))
                else:
                    new_moves.append(move)
            vals['move_ids_without_package'] = new_moves

        return super().create(vals)

    def action_confirm(self):
        for picking in self:
            # Only for "returns" picking type, don't merge!
            if picking.picking_type_id.picking_process_type == 'returns':
                # Confirm each draft move individually, avoiding any merge/group
                for move in picking.move_ids.filtered(lambda m: m.state == 'draft'):
                    move._action_confirm()
                # Do not call the parent method for returns pickings!
            else:
                # For other types, run Odoo's standard aggregation logic
                super(StockPicking, picking).action_confirm()
        return True