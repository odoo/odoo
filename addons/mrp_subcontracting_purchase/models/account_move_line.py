# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    def _get_price_unit_val_dif_and_relevant_qty(self):
        price_unit_val_dif, relevant_qty = super()._get_price_unit_val_dif_and_relevant_qty()
        if self.product_id.cost_method == 'standard' and self.purchase_line_id:
            components_cost = 0
            subcontract_production = self.purchase_line_id.move_ids._get_subcontract_production()
            components_cost -= sum(subcontract_production.move_raw_ids.stock_valuation_layer_ids.mapped('value'))
            price_unit_val_dif = price_unit_val_dif + components_cost / relevant_qty
        return price_unit_val_dif, relevant_qty

    def _get_valued_in_moves(self):
        res = super()._get_valued_in_moves()
        # subcontracted move valuations are not linked to the PO move but its orig move (the MO finished move)
        res |= res.filtered(lambda m: m.is_subcontract).move_orig_ids
        return res
