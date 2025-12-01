# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_price_unit_val_dif_and_relevant_qty(self):
        price_unit_val_dif, relevant_qty = super()._get_price_unit_val_dif_and_relevant_qty()
        if self.product_id.cost_method == 'standard' and self.purchase_line_id:
            components_cost = 0
            subcontract_production = self.purchase_line_id.move_ids._get_subcontract_production()
            components_cost = sum(subcontract_production.move_raw_ids.mapped('value'))
            qty = sum(mo.product_uom_id._compute_quantity(mo.qty_producing, self.product_uom_id) for mo in subcontract_production if mo.state == 'done')
            if not self.product_uom_id.is_zero(qty):
                price_unit_val_dif = price_unit_val_dif + components_cost / qty
        return price_unit_val_dif, relevant_qty

    def _get_stock_moves(self):
        moves = super()._get_stock_moves()
        finished_moves = set()
        for m in moves:
            if mo := m._get_subcontract_production():
                finished_moves.add(mo.move_finished_ids.filtered(lambda mf: mf.product_id == m.product_id).id)
        return moves | self.env['stock.move'].browse(finished_moves)
