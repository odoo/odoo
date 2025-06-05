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

<<<<<<< 80ab09c2a5936dc5b93a64caaa3b5c8e29cc06b2
||||||| 576d2ec1ac03b8ceb9589dd5f1115497d2d4dd9d
    def unlink(self):
        analytic_move_to_recompute = self.move_id
        res = super().unlink()
        analytic_move_to_recompute._account_analytic_entry_move()
        return res

    def _update_svl_quantity(self, added_qty):
        self.ensure_one()
        if self.state != 'done':
            return
        product_uom = self.product_id.uom_id
        added_uom_qty = self.product_uom_id._compute_quantity(added_qty, product_uom, rounding_method='HALF-UP')
        if float_is_zero(added_uom_qty, precision_rounding=product_uom.rounding):
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
        if float_is_zero(added_uom_qty, precision_rounding=product_uom.rounding):
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

>>>>>>> 0c737555ec40855b42968cad6be08135b352c684
    @api.model
    def _should_exclude_for_valuation(self):
        """
        Determines if this move line should be excluded from valuation based on its ownership.
        :return: True if the move line's owner is different from the company's partner (indicating
                it should be excluded from valuation), False otherwise.
        """
        self.ensure_one()
        return self.owner_id and self.owner_id != self.company_id.partner_id
