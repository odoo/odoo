from odoo import _, api, models
from odoo.exceptions import UserError


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super()._get_new_picking_values()
        orders = self.reference_ids.pos_order_ids
        if orders:
            order = orders.filtered(lambda o: o.is_refund_or_negative() and o.state == 'paid')[:1] or orders[:1]
            vals['pos_session_id'] = order.session_id.id
            vals['pos_order_id'] = order.id
        return vals

    def _key_assign_picking(self):
        keys = super()._key_assign_picking()
        return keys + (self.reference_ids.pos_order_ids,)

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
            existing_lots = self.env['stock.lot'].with_context(skip_preprocess_gs1=True).search([
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

    def _use_pos_lots(self):
        self.ensure_one()
        return self.product_id.tracking in ('lot', 'serial') and (
            self.picking_type_id.use_existing_lots or self.picking_type_id.use_create_lots
        )

    def _assign_pos_lots(self, lines, lots_by_name, force=False):
        """ Put on the move the lots entered on the PoS order `lines` of its product.

        With `force`, the goods already left the shop: each lot gets its quantity whatever
        the stock says. Otherwise, only what the stock has is reserved on each lot. The
        move never gets more than its demand.

        :param lots_by_name: the lots of the order, by (product, lot name)
        """
        self.ensure_one()
        product_uom = self.product_id.uom_id
        remaining = self.product_qty
        lot_quantities = [
            lot_quantity
            for line in lines.filtered(lambda l: l.product_id == self.product_id)
            for lot_quantity in line._get_lot_quantities()
        ]
        for lot_name, quantity in lot_quantities:
            quantity = min(quantity, remaining)
            if product_uom.is_zero(quantity):
                break
            remaining -= quantity
            lot = lots_by_name.get((self.product_id, lot_name))
            if lot and force:
                self._force_lot_quantity(lot, quantity=quantity)
            elif lot and not self._should_bypass_reservation():
                self._update_reserved_quantity(quantity, self.location_id, lot_id=lot, strict=False)
            elif not lot and force:
                # the lot neither exists nor can be created: keep its name for the user to fix
                self.env['stock.move.line'].create({**self._prepare_move_line_vals(quantity=quantity), 'lot_name': lot_name})

    def _check_pos_uom_conversion(self):
        """ Prevent moves whose quantity rounds to zero once converted in the product UoM. """
        uoms_with_issues = {
            (move.uom_id.name, move.product_id.uom_id.name)
            for move in self.filtered(lambda m: m.product_uom_qty and m.uom_id != m.product_id.uom_id)
            if not move.uom_id._compute_quantity(move.product_uom_qty, move.product_id.uom_id, rounding_method='HALF-UP')
        }
        if not uoms_with_issues:
            return
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

    @api.depends("product_id")
    def _compute_description_picking(self):
        super()._compute_description_picking()
        seen = set()
        for move in self:
            if not (pos_order := move.reference_ids.pos_order_ids) or move.description_picking_manual:
                continue

            product = move.product_id
            line = pos_order.lines.filtered(
                lambda l: l.product_id == product
                and l.id not in seen
                and any(av.attribute_id.create_variant == "no_variant" or av.is_custom for av in l.attribute_value_ids)
            )[:1]

            if line and move.description_picking == product.display_name:
                never_values = line.attribute_value_ids.filtered(
                    lambda av: av.attribute_id.create_variant == 'no_variant' and not av.is_custom
                )
                descriptions = never_values.mapped("display_name")
                for custom_value in line.custom_attribute_value_ids:
                    descriptions.append(f"{custom_value.display_name}")

                move.description_picking = "\n".join(descriptions) if descriptions else ""
                seen.add(line.id)
