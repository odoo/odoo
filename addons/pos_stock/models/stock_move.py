from odoo import api, models, _
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        orders = self.reference_ids.pos_order_ids
        if orders:
            order = orders.filtered(lambda o: o.is_refund and o.state == 'paid')[:1] or orders[:1]
            vals['pos_session_id'] = order.session_id.id
            vals['pos_order_id'] = order.id
        return vals

    def _key_assign_picking(self):
        keys = super()._key_assign_picking()
        return keys + (self.reference_ids.pos_order_ids,)

    @api.model
    def _prepare_lines_data_dict(self, order_lines):
        return {
            product.id: {'order_lines': lines}
            for product, lines in order_lines.grouped('product_id').items()
        }

    def _create_production_lots_for_pos_order(self, lines):
        ''' Search for existing lots and create missing ones.

            :param lines: pos order lines with pack lot ids.
            :type lines: pos.order.line recordset.

            :return stock.lot recordset.
        '''
        valid_lots = self.env['stock.lot']
        moves = self.filtered(lambda m: m.picking_type_id.use_existing_lots)
        # Already called in self._action_confirm() but just to be safe when coming from _launch_stock_rule_from_pos_order_lines.
        self._check_company()
        if moves:
            moves_product_ids = set(moves.mapped('product_id').ids)
            lots = lines.pack_lot_ids.filtered(lambda l: l.lot_name and l.product_id.id in moves_product_ids)
            lots_data = set(lots.mapped(lambda l: (l.product_id.id, l.lot_name)))
            existing_lots = self.env['stock.lot'].search([
                '|', ('company_id', '=', False), ('company_id', '=', moves[0].picking_type_id.company_id.id),
                ('product_id', 'in', lines.product_id.ids),
                ('name', 'in', lots.mapped('lot_name')),
            ])
            # The previous search may return (product_id.id, lot_name) combinations that have no matching in lines.pack_lot_ids.
            for lot in existing_lots:
                if (lot.product_id.id, lot.name) in lots_data:
                    valid_lots |= lot
                    lots_data.remove((lot.product_id.id, lot.name))
            moves = moves.filtered(lambda m: m.picking_type_id.use_create_lots)
            if moves:
                moves_product_ids = set(moves.mapped('product_id').ids)
                missing_lot_values = []
                for lot_product_id, lot_name in filter(lambda l: l[0] in moves_product_ids, lots_data):
                    missing_lot_values.append({'company_id': self.company_id.id, 'product_id': lot_product_id, 'name': lot_name})
                valid_lots |= self.env['stock.lot'].create(missing_lot_values)
        return valid_lots

    def _add_mls_related_to_order(self, related_order_lines, are_qties_done=True):
        lines_data = self._prepare_lines_data_dict(related_order_lines)
        # Moves with product_id not in related_order_lines. This can happend e.g. when product_id has a phantom-type bom.
        moves_to_assign = self.filtered(lambda m: m.product_id.id not in lines_data or m.product_id.tracking not in ['lot', 'serial']
                                                  or (not m.picking_type_id.use_existing_lots and not m.picking_type_id.use_create_lots))

        # Check for any conversion issues in the moves before setting quantities
        uoms_with_issues = set()
        for move in moves_to_assign.filtered(lambda m: m.product_uom_qty and m.uom_id != m.product_id.uom_id):
            converted_qty = move.uom_id._compute_quantity(
                move.product_uom_qty,
                move.product_id.uom_id,
                rounding_method='HALF-UP'
            )
            if not converted_qty:
                uoms_with_issues.add(
                    (move.uom_id.name, move.product_id.uom_id.name)
                )

        if uoms_with_issues:
            error_message_lines = [
                _("Conversion Error: The following unit of measure conversions result in a zero quantity due to rounding:")
            ]
            for uom_from, uom_to in uoms_with_issues:
                error_message_lines.append(_(' - From "%(uom_from)s" to "%(uom_to)s"', uom_from=uom_from, uom_to=uom_to))

            error_message_lines.append(
                _("\nThis issue occurs because the quantity becomes zero after rounding during the conversion. "
                "To fix this, adjust the conversion factors or rounding method to ensure that even the smallest quantity in the original unit "
                "does not round down to zero in the target unit.")
            )

            raise UserError('\n'.join(error_message_lines))

        for move in moves_to_assign:
            move.quantity = move.product_uom_qty
        moves_remaining = self - moves_to_assign
        existing_lots = moves_remaining._create_production_lots_for_pos_order(related_order_lines)
        move_lines_to_create = []
        if are_qties_done:
            for move in moves_remaining:
                move.move_line_ids.unlink()
                for line in lines_data[move.product_id.id]['order_lines']:
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        qty = 1 if line.product_id.tracking == 'serial' else abs(line.qty)
                        if existing_lots:
                            existing_lot = existing_lots.filtered_domain([('product_id', '=', line.product_id.id), ('name', '=', lot.lot_name)])
                            quants = self.env['stock.quant']
                            if existing_lot:
                                quants = self.env['stock.quant'].search(
                                    [('lot_id', '=', existing_lot.id), ('quantity', '>', '0.0'), ('location_id', 'child_of', move.location_id.id)],
                                    order='id desc',
                                )
                            qty_left_to_assign = qty
                            for quant in quants:
                                if qty_left_to_assign <= 0:
                                    break
                                qty_chg = min(qty_left_to_assign, quant.quantity)
                                ml_vals = dict(move._prepare_move_line_vals(qty_chg))
                                qty_left_to_assign -= qty_chg
                                ml_vals.update({
                                    'quant_id': quant.id,
                                })
                                move_lines_to_create.append(ml_vals)
                            if qty_left_to_assign > 0:
                                ml_vals = dict(move._prepare_move_line_vals(qty_left_to_assign))
                                ml_vals.update({
                                    'lot_name': existing_lot.name,
                                    'lot_id': existing_lot.id,
                                })
                                move_lines_to_create.append(ml_vals)
                        else:
                            ml_vals = dict(move._prepare_move_line_vals(qty))
                            ml_vals.update({'lot_name': lot.lot_name})
                            move_lines_to_create.append(ml_vals)

            self.env['stock.move.line'].create(move_lines_to_create)
        else:
            for move in moves_remaining:
                for line in lines_data[move.product_id.id]['order_lines']:
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        if line.product_id.tracking == 'serial':
                            qty = 1
                        else:
                            qty = abs(line.qty)
                        if existing_lots:
                            existing_lot = existing_lots.filtered_domain([('product_id', '=', line.product_id.id), ('name', '=', lot.lot_name)])
                            if existing_lot:
                                move._update_reserved_quantity(qty, move.location_id, lot_id=existing_lot)
