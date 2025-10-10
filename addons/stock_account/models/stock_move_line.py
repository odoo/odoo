from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        mls = super().create(vals_list)
        mls._update_stock_move_value()
        return mls

    def write(self, vals):
        valuation_fields = ['quantity', 'location_id', 'location_dest_id', 'owner_id', 'quant_id', 'lot_id']
        valuation_trigger = any(field in vals for field in valuation_fields)
        qty_by_ml_id = {}
        if valuation_trigger:
            for ml in self:
                if not (ml.move_id.is_in or ml.move_id.is_out):
                    continue
                qty_by_ml_id[ml] = ml.quantity
        res = super().write(vals)
        if valuation_trigger and qty_by_ml_id:
            self._update_stock_move_value(qty_by_ml_id)
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

    def _update_stock_move_value(self, old_qty_by_ml=None):
        move_to_update = set()
        if not old_qty_by_ml:
            old_qty_by_ml = {}

        for move, mls in self.grouped('move_id').items():
            if not (move.is_in or move.is_out):
                continue
            if move.is_in:
                move_to_update.add(move.id)
            elif move.is_out:
                delta = sum(
                    ml.quantity - old_qty_by_ml.get(ml, 0)
                    for ml in mls
                    if not ml._should_exclude_for_valuation()
                )
                if delta:
                    move._set_value(correction_quantity=delta)
        if move_to_update:
            self.env['stock.move'].browse(move_to_update)._set_value()
