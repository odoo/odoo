from odoo import Command, models, api


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _inverse_description_picking(self):
        super()._inverse_description_picking()
        for move in self:
            # add the description to related lines if it has a value and belongs to a repair order
            if move.repair_id and move.description_picking_manual and move.sale_line_id:
                move.sale_line_id.name = move.description_picking

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        for move, vals in zip(self, vals_list):
            if 'repair_id' in default or move.repair_id:
                vals['sale_line_id'] = False
        return vals_list

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        moves.filtered(lambda m: m.repair_id)._create_repair_linked_line()
        return moves

    def write(self, vals):
        res = super().write(vals)
        repair_moves = self.env['stock.move']
        moves_to_create_linked_line = self.env['stock.move']
        for move in self:
            if not move.repair_id:
                continue
            # checks vals update
            if (
                not move.sale_line_id
                and "sale_line_id" not in vals
                and move.repair_line_type == "add"
            ):
                moves_to_create_linked_line |= move
            if move.sale_line_id and any(field in vals for field in ('repair_line_type', 'product_uom_qty', 'uom_id', 'product_id')):
                repair_moves |= move

        repair_moves._update_repair_linked_line()
        moves_to_create_linked_line._create_repair_linked_line()
        return res

    @api.ondelete(at_uninstall=True)
    def _unlink_stock_move_linked_lines(self):
        self._clean_repair_linked_lines()

    # Needed to also cancel the lastly added part
    def _action_cancel(self):
        self._clean_repair_linked_lines()
        return super()._action_cancel()

    def _create_repair_invoice_line(self):
        invoice_lines_vals = []
        for move in self:
            invoice_id = move.repair_id.invoice_ids.filtered(lambda invoice: invoice.state != 'posted')
            if move.invoice_line_ids or move.repair_line_type != 'add' or not invoice_id:
                continue
            product_qty = move.product_uom_qty if move.repair_id.state != 'done' else move.quantity
            invoice_lines_vals.append({
                'move_id': invoice_id[0].id,  # Add to the most recent 'draft' invoice
                'product_id': move.product_id.id,
                'quantity': product_qty,
                'product_uom_id': move.uom_id.id,
                'stock_move_id': move.id,
            })
            if move.repair_id.under_warranty:
                invoice_lines_vals[-1]['price_unit'] = 0.0
            elif move.price_unit:
                invoice_lines_vals[-1]['price_unit'] = move.price_unit

        self.env['account.move.line'].create(invoice_lines_vals)

    def _create_repair_sale_order_line(self):
        so_line_vals = []
        for move in self:
            if move.sale_line_id or move.repair_line_type != 'add' or not move.repair_id.sale_order_id:
                continue
            product_qty = move.product_uom_qty if move.repair_id.state != 'done' else move.quantity
            so_line_vals.append({
                'order_id': move.repair_id.sale_order_id.id,
                'product_id': move.product_id.id,
                'product_uom_qty': product_qty,  # When relying only on so_line compute method, the sol quantity is only updated on next sol creation
                'product_uom_id': move.uom_id.id,
                'move_ids': [Command.link(move.id)],
                'qty_delivered': move.quantity if move.state == 'done' else 0.0,
            })
            if move.repair_id.under_warranty:
                so_line_vals[-1]['price_unit'] = 0.0
            elif move.price_unit:
                so_line_vals[-1]['price_unit'] = move.price_unit

        self.env['sale.order.line'].create(so_line_vals)

    def _clean_repair_linked_lines(self):
        if self.repair_id.sale_order_id:
            self.filtered(
                lambda m: m.repair_id and m.sale_line_id
            ).sale_line_id.write({'product_uom_qty': 0.0})

    def _pre_update_repair_linked_lines(self):
        moves_to_clean = self.env['stock.move']
        moves_to_update = self.env['stock.move']
        for move in self:
            if not move.repair_id:
                continue
            if move.sale_line_id and move.repair_line_type != 'add':
                moves_to_clean |= move
            if move.sale_line_id and move.repair_line_type == 'add':
                moves_to_update |= move
        moves_to_clean._clean_repair_linked_lines()
        return moves_to_update

    def _update_repair_linked_line(self):
        if self.repair_id.sale_order_id:
            return self._update_repair_sale_order_line()

    def _create_repair_linked_line(self):
        if self.repair_id.sale_order_id:
            return self._create_repair_sale_order_line()
        if self.repair_id.invoice_ids:
            return self._create_repair_invoice_line()

    def _update_repair_sale_order_line(self):
        moves_to_update = self._pre_update_repair_linked_lines()
        lines_to_recreate = self.env['stock.move']
        for move in moves_to_update:
            if move.product_id != move.sale_line_id.product_id:
                lines_to_recreate |= move
                continue

            move.sale_line_id.write({
                'product_uom_id': move.uom_id.id,
                'product_uom_qty': move.product_uom_qty if move.repair_id.state != 'done' else move.quantity,
                'discount': move.sale_line_id.discount,
            })
        # If we change the product we have to unlink the current sale_line and create a new one
        # to avoid inconsistencies and ensure everything is computed correctly.
        lines_to_recreate.description_picking = ""
        lines_to_recreate.sale_line_id.unlink()
        lines_to_recreate._create_repair_sale_order_line()

        if moves_to_update.repair_id.under_warranty:
            moves_to_update.price_unit = 0.0
