from openerp.osv import osv


class stock_picking_account_move(osv.osv_memory):
    """
    This wizard will make all account_move from picking
    """
    _name = "stock.picking.account.move"
    _description = "Move all selected picking to account_move"

    def pick_move(self, cr, uid, ids, context=None):
        stock_picking_obj = self.pool.get("stock.picking")
        account_move_obj = self.pool.get("account.move")
        stock_move_obj = self.pool.get("stock.move")
        if context:
            active_ids =  context.get("active_ids", False)
            if active_ids:
                for move_line in stock_picking_obj.browse(cr, uid, active_ids):
                    name = move_line.name
                    if not account_move_obj.search(cr, uid, [("ref", "=", name)]) and move_line.state == "done":
                        for move in move_line.move_lines:
                            context.update({"active_ids": [move_line.id], "active_id": move_line.id, "late_move": True})
                            stock_move_obj._create_product_valuation_moves(cr, uid, move, context=context)
        return {'type': 'ir.actions.act_window_close'}

stock_picking_account_move()
