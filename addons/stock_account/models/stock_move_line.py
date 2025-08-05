from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        mls = super().create(vals_list)
        if any(move.is_valued for move in mls.move_id):
            mls.move_id._set_value()
        return mls

    def write(self, vals):
        move_to_update = set()
        valuation_fields = ['qty_done', 'location_id', 'location_dest_id', 'owner_id', 'quant_id', 'lot_id']
        valuation_trigger = any(field in vals for field in valuation_fields)
        if valuation_trigger:
            move_to_update.update(self.move_id.filtered(lambda m: m.is_valued).ids)
        res = super().write(vals)
        if valuation_trigger:
            move_to_update.update(self.move_id.filtered(lambda m: m.is_valued).ids)
        if move_to_update:
            self.env['stock.move'].browse(move_to_update)._set_value()
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
