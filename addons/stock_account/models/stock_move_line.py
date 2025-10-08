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
        qty_by_ml = {}
        if valuation_trigger:
            qty_by_ml = {ml: ml.quantity for ml in self if ml.move_id.is_in or ml.move_id.is_out}
        res = super().write(vals)
        if valuation_trigger and qty_by_ml:
            self._update_stock_move_value(qty_by_ml)
        return res

<<<<<<< 6be947718c69b15f20c6680dd35e2fed5d636d28
||||||| dae9b0a906e86a9e26cd1b37bd9b9385804c8e55
    def unlink(self):
        analytic_move_to_recompute = self.move_id
        res = super().unlink()
        analytic_move_to_recompute._account_analytic_entry_move()
        return res

    def _update_svl_quantity(self, added_qty):
        self.ensure_one()
        if self.state != 'done':
            return
        if self.product_id.lot_valuated and not self.lot_id:
            raise UserError(_('This product is valuated by lot: an explicit Lot/Serial number is required when adding quantity'))
        product_uom = self.product_id.uom_id
        added_uom_qty = self.product_uom_id._compute_quantity(added_qty, product_uom, rounding_method='HALF-UP')
        if product_uom.is_zero(added_uom_qty):
            return
        self._create_correction_svl(self.move_id, added_uom_qty)

    def _action_done(self):
        for line in self:
            if not line.lot_id and not line.lot_name and line.product_id.lot_valuated:
                raise UserError(_("Lot/Serial number is mandatory for product valuated by lot"))
        return super()._action_done()

    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    def _create_correction_svl(self, move, diff):
        lot = self.lot_id if self.product_id.lot_valuated else self.env['stock.lot']
        qty = (lot, abs(diff))
        stock_valuation_layers = self.env['stock.valuation.layer']
        if (move._is_in() and diff > 0) or (move._is_out() and diff < 0):
            move.product_price_update_before_done(forced_qty=(lot, diff))
            stock_valuation_layers |= move._create_in_svl(forced_quantity=qty)
            if move.product_id.cost_method in ('average', 'fifo'):
                move.product_id._run_fifo_vacuum(move.company_id)
        elif (move._is_in() and diff < 0) or (move._is_out() and diff > 0):
            stock_valuation_layers |= move._create_out_svl(forced_quantity=qty)
            if move.product_id.lot_valuated:
                move._product_price_update_after_done()
        elif (move._is_dropshipped() and diff > 0) or (move._is_dropshipped_returned() and diff < 0):
            stock_valuation_layers |= move._create_dropshipped_svl(forced_quantity=qty)
        elif (move._is_dropshipped() and diff < 0) or (move._is_dropshipped_returned() and diff > 0):
            stock_valuation_layers |= move._create_dropshipped_returned_svl(forced_quantity=qty)

        stock_valuation_layers._validate_accounting_entries()

=======
    def unlink(self):
        analytic_move_to_recompute = self.move_id
        res = super().unlink()
        analytic_move_to_recompute._account_analytic_entry_move()
        return res

    def _update_svl_quantity(self, added_qty):
        self.ensure_one()
        if self.state != 'done':
            return
        if self.product_id.lot_valuated and not self.lot_id:
            raise UserError(_('This product is valuated by lot: an explicit Lot/Serial number is required when adding quantity'))
        product_uom = self.product_id.uom_id
        added_uom_qty = self.product_uom_id._compute_quantity(added_qty, product_uom, rounding_method='HALF-UP')
        if product_uom.is_zero(added_uom_qty):
            return
        self._create_correction_svl(self.move_id, added_uom_qty)

    def _action_done(self):
        for line in self:
            if not line.lot_id and not line.lot_name and line.product_id.lot_valuated and line.quantity:
                raise UserError(_("Lot/Serial number is mandatory for product valuated by lot"))
        return super()._action_done()

    # -------------------------------------------------------------------------
    # SVL creation helpers
    # -------------------------------------------------------------------------
    def _create_correction_svl(self, move, diff):
        lot = self.lot_id if self.product_id.lot_valuated else self.env['stock.lot']
        qty = (lot, abs(diff))
        stock_valuation_layers = self.env['stock.valuation.layer']
        if (move._is_in() and diff > 0) or (move._is_out() and diff < 0):
            move.product_price_update_before_done(forced_qty=(lot, diff))
            stock_valuation_layers |= move._create_in_svl(forced_quantity=qty)
            if move.product_id.cost_method in ('average', 'fifo'):
                move.product_id._run_fifo_vacuum(move.company_id)
        elif (move._is_in() and diff < 0) or (move._is_out() and diff > 0):
            stock_valuation_layers |= move._create_out_svl(forced_quantity=qty)
            if move.product_id.lot_valuated:
                move._product_price_update_after_done()
        elif (move._is_dropshipped() and diff > 0) or (move._is_dropshipped_returned() and diff < 0):
            stock_valuation_layers |= move._create_dropshipped_svl(forced_quantity=qty)
        elif (move._is_dropshipped() and diff < 0) or (move._is_dropshipped_returned() and diff > 0):
            stock_valuation_layers |= move._create_dropshipped_returned_svl(forced_quantity=qty)

        stock_valuation_layers._validate_accounting_entries()

>>>>>>> cc15a5e4ea7b29998a27bbed2d441d2eb298d50c
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
