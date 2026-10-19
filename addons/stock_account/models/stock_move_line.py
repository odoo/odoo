from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        mls = super().create(vals_list)
        valued_moves = mls.move_id.filtered(lambda m: m.is_in or m.is_out)
        if valued_moves:
            valued_moves._set_value(recompute_date=min(valued_moves.mapped('date')))
        return mls

    def write(self, vals):
        analytic_move_to_recompute = set()
        if 'quantity' in vals or 'move_id' in vals:
            for move_line in self:
                move_id = vals.get('move_id') or move_line.move_id.id
                analytic_move_to_recompute.add(move_id)
        valuation_fields = ['quantity', 'location_id', 'location_dest_id', 'owner_id', 'quant_id', 'lot_id']
        valuation_trigger = any(field in vals for field in valuation_fields)
        valued_moves = self.env['stock.move']
        if valuation_trigger:
            valued_moves = self.move_id.filtered(lambda m: m.is_in or m.is_out)
        res = super().write(vals)
        if valued_moves:
            valued_moves._set_value(recompute_date=min(valued_moves.mapped('date')))
        if analytic_move_to_recompute:
            self.env['stock.move'].browse(analytic_move_to_recompute).sudo()._create_analytic_move()
        return res

    def unlink(self):
        analytic_move_to_recompute = self.move_id
        res = super().unlink()
        analytic_move_to_recompute.sudo()._create_analytic_move()
        return res

    @api.model
    def _should_exclude_for_valuation(self):
        """
        Determines if this move line should be excluded from valuation based on its ownership.
        :return: True if the move line's owner is different from the company's partner (indicating
                it should be excluded from valuation), False otherwise.
        """
        self.ensure_one()
        return self.owner_id and self.owner_id != self.company_id.partner_id

    def _is_consigned_valued_line(self):
        """ return true if the move line would have been considered in the _get_valued_qty() method except for
        the _should_exclude_for_valuation criteria (.i.e the line would have been valued if it wasn't consigned)
        """
        return self.picked and self._should_exclude_for_valuation() and\
            (not self.location_id._should_be_valued() and self.location_dest_id._should_be_valued()
            or self.location_id._should_be_valued() and not self.location_dest_id._should_be_valued())
