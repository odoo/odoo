# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, Command, fields, models, _
from odoo.tools.float_utils import float_compare, float_is_zero, float_round
from odoo.exceptions import UserError


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    def _ondelete_stock_moves(self):
        modified_fields = ['qty_received_manual', 'qty_received_method']
        self.flush_recordset(fnames=['qty_received', *modified_fields])
        self.invalidate_recordset(fnames=modified_fields, flush=False)
        query = f'''
            UPDATE {self._table}
            SET qty_received_manual = qty_received, qty_received_method = 'manual'
            WHERE id IN %(ids)s
        '''
        self.env.cr.execute(query, {'ids': self._ids or (None,)})
        self.modified(modified_fields)

    qty_received_method = fields.Selection(selection_add=[('stock_moves', 'Stock Moves')],
                                           ondelete={'stock_moves': _ondelete_stock_moves})

    move_ids = fields.One2many('stock.move', 'purchase_line_id', string='Reservation', readonly=True, copy=False)
    orderpoint_id = fields.Many2one('stock.warehouse.orderpoint', 'Orderpoint', copy=False, index='btree_not_null')
    move_dest_ids = fields.Many2many('stock.move', 'stock_move_created_purchase_line_rel', 'created_purchase_line_id', 'move_id', 'Downstream moves alt')
    product_description_variants = fields.Char('Custom Description')
    propagate_cancel = fields.Boolean('Propagate cancellation', default=True)
    forecasted_issue = fields.Boolean(compute='_compute_forecasted_issue')
    location_final_id = fields.Many2one('stock.location', 'Location from procurement')
    group_id = fields.Many2one('procurement.group', 'Procurement group that generated this line')

    def _compute_qty_received_method(self):
        super(PurchaseOrderLine, self)._compute_qty_received_method()
        for line in self.filtered(lambda l: not l.display_type):
            if line.product_id.type == 'consu':
                line.qty_received_method = 'stock_moves'

    def _get_po_line_moves(self):
        self.ensure_one()
        moves = self.move_ids.filtered(lambda m: m.product_id == self.product_id)
        if self._context.get('accrual_entry_date'):
            moves = moves.filtered(lambda r: fields.Date.context_today(r, r.date) <= self._context['accrual_entry_date'])
        return moves

    @api.depends('move_ids.state', 'move_ids.product_uom', 'move_ids.quantity')
    def _compute_qty_received(self):
        from_stock_lines = self.filtered(lambda order_line: order_line.qty_received_method == 'stock_moves')
        super(PurchaseOrderLine, self - from_stock_lines)._compute_qty_received()
        for line in self:
            if line.qty_received_method == 'stock_moves':
                total = 0.0
                # In case of a BOM in kit, the products delivered do not correspond to the products in
                # the PO. Therefore, we can skip them since they will be handled later on.
                for move in line._get_po_line_moves():
                    if move.state == 'done':
                        if move._is_purchase_return():
                            if move.to_refund:
                                total -= move.product_uom._compute_quantity(move.quantity, line.product_uom, rounding_method='HALF-UP')
                        elif move.origin_returned_move_id and move.origin_returned_move_id._is_dropshipped() and not move._is_dropshipped_returned():
                            # Edge case: the dropship is returned to the stock, no to the supplier.
                            # In this case, the received quantity on the PO is set although we didn't
                            # receive the product physically in our stock. To avoid counting the
                            # quantity twice, we do nothing.
                            pass
                        elif move.origin_returned_move_id and move.origin_returned_move_id._is_purchase_return() and not move.to_refund:
                            pass
                        else:
                            total += move.product_uom._compute_quantity(move.quantity, line.product_uom, rounding_method='HALF-UP')
                line._track_qty_received(total)
                line.qty_received = total

    @api.depends('product_uom_qty', 'date_planned')
    def _compute_forecasted_issue(self):
        for line in self:
            warehouse = line.order_id.picking_type_id.warehouse_id
            line.forecasted_issue = False
            if line.product_id:
                virtual_available = line.product_id.with_context(warehouse_id=warehouse.id, to_date=line.date_planned).virtual_available
                if line.state == 'draft':
                    virtual_available += line.product_uom_qty
                if virtual_available < 0:
                    line.forecasted_issue = True

    @api.model_create_multi
    def create(self, vals_list):
        lines = super(PurchaseOrderLine, self).create(vals_list)
        lines.filtered(lambda l: l.order_id.state == 'purchase')._create_or_update_picking()
        return lines

    def write(self, values):
        if values.get('date_planned'):
            new_date = fields.Datetime.to_datetime(values['date_planned'])
            self.filtered(lambda l: not l.display_type)._update_move_date_deadline(new_date)
        lines = self.filtered(lambda l: l.order_id.state == 'purchase'
                                        and not l.display_type)

        if 'product_packaging_id' in values:
            self.move_ids.filtered(
                lambda m: m.state not in ['cancel', 'done']
            ).product_packaging_id = values['product_packaging_id']

        previous_product_uom_qty = {line.id: line.product_uom_qty for line in lines}
        previous_product_qty = {line.id: line.product_qty for line in lines}
        result = super(PurchaseOrderLine, self).write(values)
        if 'price_unit' in values:
            for line in lines:
                # Avoid updating kit components' stock.move
                moves = line.move_ids.filtered(lambda s: s.state not in ('cancel', 'done') and s.product_id == line.product_id)
                moves.write({'price_unit': line._get_stock_move_price_unit()})
        if 'product_qty' in values:
            lines = lines.filtered(lambda l: float_compare(previous_product_qty[l.id], l.product_qty, precision_rounding=l.product_uom.rounding) != 0)
            lines.with_context(previous_product_qty=previous_product_uom_qty)._create_or_update_picking()
        return result

    def action_product_forecast_report(self):
        self.ensure_one()
        action = self.product_id.action_product_forecast_report()
        action['context'] = {
            'active_id': self.product_id.id,
            'active_model': 'product.product',
            'move_to_match_ids': self.move_ids.filtered(lambda m: m.product_id == self.product_id).ids,
            'purchase_line_to_match_id': self.id,
        }
        warehouse = self.order_id.picking_type_id.warehouse_id
        if warehouse:
            action['context']['warehouse_id'] = warehouse.id
        return action

    def unlink(self):
        self.move_ids._action_cancel()

        # Unlink move_dests that have other created_purchase_line_ids instead of cancelling them
        for line in self:
            moves_to_unlink = line.move_dest_ids.filtered(lambda m: len(m.created_purchase_line_ids.ids) > 1)
            if moves_to_unlink:
                moves_to_unlink.created_purchase_line_ids = [Command.unlink(line.id)]

        ppg_cancel_lines = self.filtered(lambda line: line.propagate_cancel)
        ppg_cancel_lines.move_dest_ids._action_cancel()

        not_ppg_cancel_lines = self.filtered(lambda line: not line.propagate_cancel)
        not_ppg_cancel_lines.move_dest_ids.write({'procure_method': 'make_to_stock'})
        not_ppg_cancel_lines.move_dest_ids._recompute_state()

        return super().unlink()

    # --------------------------------------------------
    # Business methods
    # --------------------------------------------------

    def _update_move_date_deadline(self, new_date):
        """ Updates corresponding move picking line deadline dates that are not yet completed. """
        moves_to_update = self.move_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        if not moves_to_update:
            moves_to_update = self.move_dest_ids.filtered(lambda m: m.state not in ('done', 'cancel'))
        for move in moves_to_update:
            move.date_deadline = new_date

    def _create_or_update_picking(self):
        for line in self:
            if line.product_id and line.product_id.type == 'consu':
                rounding = line.product_uom.rounding
                # Prevent decreasing below received quantity
                if float_compare(line.product_qty, line.qty_received, precision_rounding=rounding) < 0:
                    raise UserError(_('You cannot decrease the ordered quantity below the received quantity.\n'
                                      'Create a return first.'))

                if float_compare(line.product_qty, line.qty_invoiced, precision_rounding=rounding) < 0 and line.invoice_lines:
                    # If the quantity is now below the invoiced quantity, create an activity on the vendor bill
                    # inviting the user to create a refund.
                    line.invoice_lines[0].move_id.activity_schedule(
                        'mail.mail_activity_data_warning',
                        note=_('The quantities on your purchase order indicate less than billed. You should ask for a refund.'))

                # If the user increased quantity of existing line or created a new line
                # Give priority to the pickings related to the line
                line_pickings = line.move_ids.picking_id.filtered(lambda p: p.state not in ('done', 'cancel') and p.location_dest_id.usage in ('internal', 'transit', 'customer'))
                if line_pickings:
                    picking = line_pickings[0]
                else:
                    pickings = line.order_id.picking_ids.filtered(lambda x: x.state not in ('done', 'cancel') and x.location_dest_id.usage in ('internal', 'transit', 'customer'))
                    picking = pickings and pickings[0] or False
                if not picking:
                    if not line.product_qty > line.qty_received:
                        continue
                    res = line.order_id._prepare_picking()
                    picking = self.env['stock.picking'].create(res)

                moves = line._create_stock_moves(picking)
                moves._action_confirm()._action_assign()

    def _get_stock_move_price_unit(self):
        self.ensure_one()
        order = self.order_id
        price_unit = self.price_unit
        price_unit_prec = self.env['decimal.precision'].precision_get('Product Price')
        if self.taxes_id:
            qty = self.product_qty or 1
            price_unit = self.taxes_id.compute_all(
                price_unit,
                currency=self.order_id.currency_id,
                quantity=qty,
                product=self.product_id,
                partner=self.order_id.partner_id,
                rounding_method="round_globally",
            )['total_void']
            price_unit = price_unit / qty
        if self.product_uom.id != self.product_id.uom_id.id:
            price_unit *= self.product_uom.factor / self.product_id.uom_id.factor
        if order.currency_id != order.company_id.currency_id:
            price_unit = order.currency_id._convert(
                price_unit, order.company_id.currency_id, self.company_id, self.date_order or fields.Date.today(), round=False)
        return float_round(price_unit, precision_digits=price_unit_prec)

    def _get_move_dests_initial_demand(self, move_dests):
        return self.product_id.uom_id._compute_quantity(
            sum(move_dests.filtered(lambda m: m.state != 'cancel' and m.location_dest_id.usage != 'supplier').mapped('product_qty')),
            self.product_uom, rounding_method='HALF-UP')

    def _prepare_stock_moves(self, picking):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type != 'consu':
            return res

        price_unit = self._get_stock_move_price_unit()
        qty = self._get_qty_procurement()

        move_dests = self.move_dest_ids or self.move_ids.move_dest_ids
        move_dests = move_dests.filtered(lambda m: m.state != 'cancel' and not m._is_purchase_return())

        if not move_dests:
            qty_to_attach = 0
            qty_to_push = self.product_qty - qty
        else:
            move_dests_initial_demand = self._get_move_dests_initial_demand(move_dests)
            qty_to_attach = move_dests_initial_demand - qty
            qty_to_push = self.product_qty - move_dests_initial_demand

        if float_compare(qty_to_attach, 0.0, precision_rounding=self.product_uom.rounding) > 0:
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_attach, self.product_id.uom_id)
            res.append(self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom))
        if not float_is_zero(qty_to_push, precision_rounding=self.product_uom.rounding):
            product_uom_qty, product_uom = self.product_uom._adjust_uom_quantities(qty_to_push, self.product_id.uom_id)
            extra_move_vals = self._prepare_stock_move_vals(picking, price_unit, product_uom_qty, product_uom)
            extra_move_vals['move_dest_ids'] = False  # don't attach
            res.append(extra_move_vals)
        return res

    def _get_qty_procurement(self):
        self.ensure_one()
        qty = 0.0
        outgoing_moves, incoming_moves = self._get_outgoing_incoming_moves()
        for move in outgoing_moves:
            qty_to_compute = move.quantity if move.state == 'done' else move.product_uom_qty
            qty -= move.product_uom._compute_quantity(qty_to_compute, self.product_uom, rounding_method='HALF-UP')
        for move in incoming_moves:
            qty_to_compute = move.quantity if move.state == 'done' else move.product_uom_qty
            qty += move.product_uom._compute_quantity(qty_to_compute, self.product_uom, rounding_method='HALF-UP')
        return qty

    def _check_orderpoint_picking_type(self):
        warehouse_loc = self.order_id.picking_type_id.warehouse_id.view_location_id
        dest_loc = self.move_dest_ids.location_id or self.orderpoint_id.location_id
        if warehouse_loc and dest_loc and dest_loc.warehouse_id and not warehouse_loc.parent_path in dest_loc[0].parent_path:
            raise UserError(_('The warehouse of operation type (%(operation_type)s) is inconsistent with location (%(location)s) of reordering rule (%(reordering_rule)s) for product %(product)s. Change the operation type or cancel the request for quotation.',
                              product=self.product_id.display_name, operation_type=self.order_id.picking_type_id.display_name, location=self.orderpoint_id.location_id.display_name, reordering_rule=self.orderpoint_id.display_name))

    def _prepare_stock_move_vals(self, picking, price_unit, product_uom_qty, product_uom):
        self.ensure_one()
        self._check_orderpoint_picking_type()
        product = self.product_id.with_context(lang=self.order_id.dest_address_id.lang or self.env.user.lang)
        location_dest = self.env['stock.location'].browse(self.order_id._get_destination_location())
        location_final = self.location_final_id or self.order_id._get_final_location_record()
        if location_final and location_final._child_of(location_dest):
            location_dest = location_final
        date_planned = self.date_planned or self.order_id.date_planned
        return {
            # truncate to 2000 to avoid triggering index limit error
            # TODO: remove index in master?
            'name': (self.product_id.display_name or '')[:2000],
            'product_id': self.product_id.id,
            'date': date_planned,
            'date_deadline': date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': location_dest.id,
            'location_final_id': location_final.id,
            'picking_id': picking.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_ids': [(4, x) for x in self.move_dest_ids.ids],
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': self.order_id.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'origin': self.order_id.name,
            'description_picking': product.description_pickingin or self.name,
            'propagate_cancel': self.propagate_cancel,
            'warehouse_id': self.order_id.picking_type_id.warehouse_id.id,
            'product_uom_qty': product_uom_qty,
            'product_uom': product_uom.id,
            'product_packaging_id': self.product_packaging_id.id,
            'sequence': self.sequence,
        }

    @api.model
    def _prepare_purchase_order_line_from_procurement(self, product_id, product_qty, product_uom, location_dest_id, name, origin, company_id, values, po):
        line_description = ''
        if values.get('product_description_variants'):
            line_description = values['product_description_variants']
        supplier = values.get('supplier')
        res = self._prepare_purchase_order_line(product_id, product_qty, product_uom, company_id, supplier, po)
        # We need to keep the vendor name set in _prepare_purchase_order_line. To avoid redundancy
        # in the line name, we add the line_description only if different from the product name.
        # This way, we shoud not lose any valuable information.
        if line_description and product_id.name != line_description:
            res['name'] += '\n' + line_description
        res['date_planned'] = values.get('date_planned')
        res['move_dest_ids'] = [(4, x.id) for x in values.get('move_dest_ids', [])]
        res['location_final_id'] = location_dest_id.id
        res['orderpoint_id'] = values.get('orderpoint_id', False) and values.get('orderpoint_id').id
        res['propagate_cancel'] = values.get('propagate_cancel')
        res['product_description_variants'] = values.get('product_description_variants')
        res['product_no_variant_attribute_value_ids'] = values.get('never_product_template_attribute_value_ids')

        # Need to attach purchase order to procurement group for mtso
        group = values.get('group_id')
        if group and not res['move_dest_ids']:
            res['group_id'] = values['group_id'].id
        return res

    def _create_stock_moves(self, picking):
        values = []
        for line in self.filtered(lambda l: not l.display_type):
            for val in line._prepare_stock_moves(picking):
                values.append(val)
            line.move_dest_ids.created_purchase_line_ids = [Command.clear()]

        return self.env['stock.move'].create(values)

    def _find_candidate(self, product_id, product_qty, product_uom, location_id, name, origin, company_id, values):
        """ Return the record in self where the procument with values passed as
        args can be merged. If it returns an empty record then a new line will
        be created.
        """
        description_picking = ''
        if values.get('product_description_variants'):
            description_picking = values['product_description_variants']
        lines = self.filtered(
            lambda l: l.propagate_cancel == values['propagate_cancel']
            and (l.orderpoint_id == values['orderpoint_id'] if values['orderpoint_id'] and not values['move_dest_ids'] else True)
        )

        # In case 'product_description_variants' is in the values, we also filter on the PO line
        # name. This way, we can merge lines with the same description. To do so, we need the
        # product name in the context of the PO partner.
        if lines and values.get('product_description_variants'):
            partner = self.mapped('order_id.partner_id')[:1]
            product_lang = product_id.with_context(
                lang=partner.lang,
                partner_id=partner.id,
            )
            name = product_lang.display_name
            if product_lang.description_purchase:
                name += '\n' + product_lang.description_purchase
            lines = lines.filtered(lambda l: l.name == name + '\n' + description_picking)
            if lines:
                return lines[0]

        return lines and lines[0] or self.env['purchase.order.line']

    def _get_outgoing_incoming_moves(self):
        outgoing_moves = self.env['stock.move']
        incoming_moves = self.env['stock.move']

        for move in self.move_ids.filtered(lambda r: r.state != 'cancel' and not r.scrapped and self.product_id == r.product_id):
            if move._is_purchase_return() and move.to_refund:
                outgoing_moves |= move
            elif move.location_dest_id.usage != "supplier":
                if not move.origin_returned_move_id or (move.origin_returned_move_id and move.to_refund):
                    incoming_moves |= move

        return outgoing_moves, incoming_moves

    def _update_date_planned(self, updated_date):
        move_to_update = self.move_ids.filtered(lambda m: m.state not in ['done', 'cancel'])
        if not self.move_ids or move_to_update:  # Only change the date if there is no move done or none
            super()._update_date_planned(updated_date)
        if move_to_update:
            self._update_move_date_deadline(updated_date)

    @api.model
    def _update_qty_received_method(self):
        """Update qty_received_method for old PO before install this module."""
        self.search(['!', ('state', 'in', ['purchase', 'done'])])._compute_qty_received_method()

    def _merge_po_line(self, rfq_line):
        super()._merge_po_line(rfq_line)
        self.move_dest_ids += rfq_line.move_dest_ids
