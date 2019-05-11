# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(StockMoveLine, self).create(vals_list)
        for line in lines:
            move = line.move_id
            if move.state == 'done':
                correction_value = move._run_valuation(line.qty_done)
                if move.product_id.valuation == 'real_time' and (move._is_in() or move._is_out()):
                    move.with_context(force_valuation_amount=correction_value)._account_entry_move()
        return lines

    def write(self, vals):
        """ When editing a done stock.move.line, we impact the valuation. Users may increase or
        decrease the `qty_done` field. There are three cost method available: standard, average
        and fifo. We implement the logic in a similar way for standard and average: increase
        or decrease the original value with the standard or average price of today. In fifo, we
        have a different logic wheter the move is incoming or outgoing. If the move is incoming, we
        update the value and remaining_value/qty with the unit price of the move. If the move is
        outgoing and the user increases qty_done, we call _run_fifo and it'll consume layer(s) in
        the stack the same way a new outgoing move would have done. If the move is outoing and the
        user decreases qty_done, we either increase the last receipt candidate if one is found or
        we decrease the value with the last fifo price.
        """
        if 'qty_done' in vals:
            moves_to_update = {}
            for move_line in self.filtered(lambda ml: ml.state == 'done' and (ml.move_id._is_in() or ml.move_id._is_out())):
                moves_to_update[move_line.move_id] = vals['qty_done'] - move_line.qty_done

            for move_id, qty_difference in moves_to_update.items():
                move_vals = {}
                if move_id.product_id.cost_method in ['standard', 'average']:
                    correction_value = qty_difference * move_id.product_id.standard_price
                    if move_id._is_in():
                        move_vals['value'] = move_id.value + correction_value
                    elif move_id._is_out():
                        move_vals['value'] = move_id.value - correction_value
                else:
                    if move_id._is_in():
                        correction_value = qty_difference * move_id.price_unit
                        new_remaining_value = move_id.remaining_value + correction_value
                        move_vals['value'] = move_id.value + correction_value
                        move_vals['remaining_qty'] = move_id.remaining_qty + qty_difference
                        move_vals['remaining_value'] = move_id.remaining_value + correction_value
                    elif move_id._is_out() and qty_difference > 0:
                        correction_value = self.env['stock.move']._run_fifo(move_id, quantity=qty_difference)
                        # no need to adapt `remaining_qty` and `remaining_value` as `_run_fifo` took care of it
                        move_vals['value'] = move_id.value - correction_value
                    elif move_id._is_out() and qty_difference < 0:
                        candidates_receipt = self.env['stock.move'].search(move_id._get_in_domain(), order='date, id desc', limit=1)
                        if candidates_receipt:
                            candidates_receipt.write({
                                'remaining_qty': candidates_receipt.remaining_qty + -qty_difference,
                                'remaining_value': candidates_receipt.remaining_value + (-qty_difference * candidates_receipt.price_unit),
                            })
                            correction_value = qty_difference * candidates_receipt.price_unit
                        else:
                            correction_value = qty_difference * move_id.product_id.standard_price
                        move_vals['value'] = move_id.value - correction_value
                move_id.write(move_vals)

                if move_id.product_id.valuation == 'real_time':
                    move_id.with_context(force_valuation_amount=correction_value, forced_quantity=qty_difference)._account_entry_move()
                if qty_difference > 0:
                    move_id.product_price_update_before_done(forced_qty=qty_difference)
        return super(StockMoveLine, self).write(vals)

