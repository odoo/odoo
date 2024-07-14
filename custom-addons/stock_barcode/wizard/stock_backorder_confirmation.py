from odoo import api, fields, models


class StockBackorderConfirmation(models.TransientModel):
    _inherit = 'stock.backorder.confirmation'

    empty_move_count = fields.Integer(compute="_compute_not_fully_processed_move_count")
    partial_move_count = fields.Integer(compute="_compute_not_fully_processed_move_count")

    @api.depends('pick_ids')
    def _compute_not_fully_processed_move_count(self):
        for backorder in self:
            moves = backorder.pick_ids.move_ids
            backorder.empty_move_count = len(moves.filtered(lambda mv: mv.product_uom_qty and not mv.picked))
            not_done_count = len(moves.filtered(lambda mv: mv.product_uom_qty > mv.quantity and mv.picked))
            backorder.partial_move_count = not_done_count - backorder.empty_move_count
