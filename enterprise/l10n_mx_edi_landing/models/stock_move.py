# coding: utf-8
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockMove(models.Model):

    _inherit = 'stock.move'

    move_orig_fifo_ids = fields.Many2many(
        'stock.move', 'stock_move_move_fifo_rel', 'move_dest_id',
        'move_orig_id', 'Original Fifo Move',
        help="Optional: previous stock move when chaining them")

    def _create_out_svl(self, forced_quantity=None):
        res = self.env['stock.valuation.layer']
        for move in self:
            product = move.product_id
            if product.cost_method not in ('average', 'fifo'):
                res |= super(StockMove, move)._create_out_svl(
                    forced_quantity=forced_quantity)
                continue
            candidates = res.sudo().search([
                ('product_id', '=', product.id),
                ('remaining_qty', '>', 0),
                ('company_id', '=', move.company_id.id),
            ])
            candidates_bfr = dict(candidates.mapped(
                lambda r: (r.id, r.remaining_qty)))
            res |= super(StockMove, move)._create_out_svl(
                forced_quantity=forced_quantity)
            for candidate in candidates_bfr:
                candidate = res.browse(candidate)
                if candidate.remaining_qty == candidates_bfr[candidate.id]:
                    continue
                if candidate.stock_move_id:
                    move.write({'move_orig_fifo_ids': [
                        (4, candidate.stock_move_id.id, 0)]})
        return res
