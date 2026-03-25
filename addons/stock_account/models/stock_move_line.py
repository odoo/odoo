from odoo import api, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    @api.model_create_multi
    def create(self, vals_list):
        mls = super().create(vals_list)
        mls._update_stock_move_value()
        return mls

    def write(self, vals):
        analytic_move_to_recompute = set()
        if 'quantity' in vals or 'move_id' in vals:
            for move_line in self:
                move_id = vals.get('move_id', move_line.move_id.id)
                analytic_move_to_recompute.add(move_id)
<<<<<<< f7c309cdac754ead9e00b3443a2fe764efec819c
        valuation_fields = ['quantity', 'location_id', 'location_dest_id', 'owner_id', 'quant_id', 'lot_id']
        valuation_trigger = any(field in vals for field in valuation_fields)
        qty_by_ml = {}
        if valuation_trigger:
            qty_by_ml = {ml: ml.quantity for ml in self if ml.move_id.is_in or ml.move_id.is_out}
||||||| 609fc42e1222d225ef7040c64080882b65d6d5ef
        new_lot = False
        if 'lot_id' in vals:
            new_lot = vals.get('lot_id')
        if 'quant_id' in vals:
            new_quant = vals.get('quant_id')
            new_lot = self.env['stock.quant'].browse(new_quant).lot_id.id
        if new_lot:
            # remove quantity of old lot
            for move_line in self:
                move_line._update_svl_quantity(-move_line.quantity)
        elif 'quantity' in vals:
            # directly updates the right quantity if no lot change
            for move_line in self:
                move_line._update_svl_quantity(vals['quantity'] - move_line.quantity)
        if 'location_id' in vals or 'location_dest_id' in vals:
            for move_line in self:
                if move_line.state != 'done':
                    continue
                new_loc_id = vals.get('location_id', move_line.location_id.id)
                new_loc = self.env['stock.location'].browse(new_loc_id)
                new_dest_loc_id = vals.get('location_dest_id', move_line.location_dest_id.id)
                new_dest_loc = self.env['stock.location'].browse(new_dest_loc_id)
                if move_line.location_id._should_be_valued() != new_loc._should_be_valued() \
                        or move_line.location_dest_id._should_be_valued() != new_dest_loc._should_be_valued():
                    raise ValidationError(_("The stock valuation of a move is based on the type of the source and destination locations. "
                                            "As the move is already processed, you cannot modify the locations in a way that changes the "
                                            "valuation logic defined during the initial processing."))
=======
        new_lot = vals.get('lot_id')
        if 'lot_id' in vals and not new_lot:
            for move_line in self:
                if move_line.product_id.lot_valuated and move_line.state == "done":
                    raise UserError(_('Product %(product)s is valuated by lot: an explicit Lot/Serial number is required.',
                        product=move_line.product_id.display_name))
        if 'quant_id' in vals:
            new_quant = vals.get('quant_id')
            new_lot = self.env['stock.quant'].browse(new_quant).lot_id.id
        if new_lot:
            # remove quantity of old lot
            for move_line in self:
                move_line._update_svl_quantity(-move_line.quantity)
        elif 'quantity' in vals:
            # directly updates the right quantity if no lot change
            for move_line in self:
                move_line._update_svl_quantity(vals['quantity'] - move_line.quantity)
        if 'location_id' in vals or 'location_dest_id' in vals:
            for move_line in self:
                if move_line.state != 'done':
                    continue
                new_loc_id = vals.get('location_id', move_line.location_id.id)
                new_loc = self.env['stock.location'].browse(new_loc_id)
                new_dest_loc_id = vals.get('location_dest_id', move_line.location_dest_id.id)
                new_dest_loc = self.env['stock.location'].browse(new_dest_loc_id)
                if move_line.location_id._should_be_valued() != new_loc._should_be_valued() \
                        or move_line.location_dest_id._should_be_valued() != new_dest_loc._should_be_valued():
                    raise ValidationError(_("The stock valuation of a move is based on the type of the source and destination locations. "
                                            "As the move is already processed, you cannot modify the locations in a way that changes the "
                                            "valuation logic defined during the initial processing."))
>>>>>>> b352d2010bfe2a28de29621be53e704cb73b20e0
        res = super().write(vals)
        if valuation_trigger and qty_by_ml:
            self._update_stock_move_value(qty_by_ml)
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

    def _update_stock_move_value(self, old_qty_by_ml=None):
        move_to_update_ids = set()
        if not old_qty_by_ml:
            old_qty_by_ml = {}

        for move, mls in self.grouped('move_id').items():
            if not (move.is_in or move.is_out):
                continue
            if move.is_in:
                move_to_update_ids.add(move.id)
            elif move.is_out:
                delta = sum(
                    ml.quantity - old_qty_by_ml.get(ml, 0)
                    for ml in mls
                    if not ml._should_exclude_for_valuation()
                )
                if delta:
                    move._set_value(correction_quantity=delta)
        if moves_to_update := self.env['stock.move'].browse(move_to_update_ids):
            moves_to_update._set_value()

    def _is_consigned_valued_line(self):
        """ return true if the move line would have been considered in the _get_valued_qty() method except for
        the _should_exclude_for_valuation criteria (.i.e the line would have been valued if it wasn't consigned)
        """
        return self.picked and self._should_exclude_for_valuation() and\
            (not self.location_id._should_be_valued() and self.location_dest_id._should_be_valued()
            or self.location_id._should_be_valued() and not self.location_dest_id._should_be_valued())
