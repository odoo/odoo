from odoo import models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    def _get_lot_partner(self):
        self.ensure_one()
        picking = self.move_id.picking_id
        if picking.is_dropship and picking.sale_id.partner_shipping_id:
            return picking.sale_id.partner_shipping_id
        return super()._get_lot_partner()

    def _action_done(self):
        dropship_move_lines = self.filtered(lambda ml: ml.picking_id.is_dropship)
        res = super()._action_done()
        for move_line in dropship_move_lines:
            if partner := move_line._get_lot_partner():
                move_line.lot_id.partner_ids |= partner
        return res
