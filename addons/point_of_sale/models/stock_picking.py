# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools import float_is_zero, float_compare

from itertools import groupby
from collections import defaultdict

class StockPicking(models.Model):
    _inherit='stock.picking'

    pos_session_id = fields.Many2one('pos.session', index=True)
    pos_order_id = fields.Many2one('pos.order', index=True)

    def _prepare_picking_vals(self, partner, picking_type, location_id, location_dest_id):
        return {
            'partner_id': partner.id if partner else False,
            'user_id': False,
            'picking_type_id': picking_type.id,
            'move_type': 'direct',
            'location_id': location_id,
            'location_dest_id': location_dest_id,
            'state': 'draft',
        }


    @api.model
    def _create_picking_from_pos_order_lines(self, location_dest_id, lines, picking_type, partner=False):
        """We'll create some picking based on order_lines"""

        pickings = self.env['stock.picking']
        stockable_lines = lines.filtered(lambda l: l.product_id.type in ['product', 'consu'] and not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding))
        if not stockable_lines:
            return pickings
        positive_lines = stockable_lines.filtered(lambda l: l.qty > 0)
        negative_lines = stockable_lines - positive_lines

        if positive_lines:
            location_id = picking_type.default_location_src_id.id
            positive_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, picking_type, location_id, location_dest_id)
            )

            positive_picking._create_move_from_pos_order_lines(positive_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    positive_picking._action_done()
            except (UserError, ValidationError):
                pass

            pickings |= positive_picking
        if negative_lines:
            if picking_type.return_picking_type_id:
                return_picking_type = picking_type.return_picking_type_id
                return_location_id = return_picking_type.default_location_dest_id.id
            else:
                return_picking_type = picking_type
                return_location_id = picking_type.default_location_src_id.id

            negative_picking = self.env['stock.picking'].create(
                self._prepare_picking_vals(partner, return_picking_type, location_dest_id, return_location_id)
            )
            negative_picking._create_move_from_pos_order_lines(negative_lines)
            self.env.flush_all()
            try:
                with self.env.cr.savepoint():
                    negative_picking._action_done()
            except (UserError, ValidationError):
                pass
            pickings |= negative_picking
        return pickings

    def _prepare_stock_move_vals(self, first_line, order_lines):
        return {
            'name': first_line.name,
            'product_uom': first_line.product_id.uom_id.id,
            'picking_id': self.id,
            'picking_type_id': self.picking_type_id.id,
            'product_id': first_line.product_id.id,
            'product_uom_qty': abs(sum(order_lines.mapped('qty'))),
            'location_id': self.location_id.id,
            'location_dest_id': self.location_dest_id.id,
            'company_id': self.company_id.id,
        }

    def _create_move_from_pos_order_lines(self, lines):
        self.ensure_one()
        lines_by_product = groupby(sorted(lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id)
        move_vals = []
        for dummy, olines in lines_by_product:
            order_lines = self.env['pos.order.line'].concat(*olines)
            move_vals.append(self._prepare_stock_move_vals(order_lines[0], order_lines))
        moves = self.env['stock.move'].create(move_vals)
        confirmed_moves = moves._action_confirm()
        confirmed_moves._add_mls_related_to_order(lines, are_qties_done=True)
        confirmed_moves.picked = True
        self._link_owner_on_return_picking(lines)

    def _link_owner_on_return_picking(self, lines):
        """This method tries to retrieve the owner of the returned product"""
        if lines[0].order_id.refunded_order_ids.picking_ids:
            returned_lines_picking = lines[0].order_id.refunded_order_ids.picking_ids
            returnable_qty_by_product = {}
            for move_line in returned_lines_picking.move_line_ids:
                returnable_qty_by_product[(move_line.product_id.id, move_line.owner_id.id or 0)] = move_line.quantity
            for move in self.move_line_ids:
                for keys in returnable_qty_by_product:
                    if move.product_id.id == keys[0] and keys[1] and returnable_qty_by_product[keys] > 0:
                        move.write({'owner_id': keys[1]})
                        returnable_qty_by_product[keys] -= move.quantity


    def _send_confirmation_email(self):
        # Avoid sending Mail/SMS for POS deliveries
        pickings = self.filtered(lambda p: p.picking_type_id != p.picking_type_id.warehouse_id.pos_type_id)
        return super(StockPicking, pickings)._send_confirmation_email()

    def _action_done(self):
        res = super()._action_done()
        for rec in self:
            if rec.picking_type_id.code != 'outgoing':
                continue
            if rec.pos_order_id.shipping_date and not rec.pos_order_id.to_invoice:
                cost_per_account = defaultdict(lambda: 0.0)
                for line in rec.pos_order_id.lines:
                    if line.product_id.type != 'product' or line.product_id.valuation != 'real_time':
                        continue
                    out = line.product_id.categ_id.property_stock_account_output_categ_id
                    exp = line.product_id._get_product_accounts()['expense']
                    cost_per_account[(out, exp)] += line.total_cost
                move_vals = []
                for (out_acc, exp_acc), cost in cost_per_account.items():
                    move_vals.append({
                        'journal_id': rec.pos_order_id.sale_journal.id,
                        'date': rec.pos_order_id.date_order,
                        'ref': 'pos_order_'+str(rec.pos_order_id.id),
                        'line_ids': [
                            (0, 0, {
                                'name': rec.pos_order_id.name,
                                'account_id': exp_acc.id,
                                'debit': cost,
                                'credit': 0.0,
                            }),
                            (0, 0, {
                                'name': rec.pos_order_id.name,
                                'account_id': out_acc.id,
                                'debit': 0.0,
                                'credit': cost,
                            }),
                        ],
                    })
                move = self.env['account.move'].sudo().create(move_vals)
                move.action_post()
        return res

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.depends('warehouse_id')
    def _compute_hide_reservation_method(self):
        super()._compute_hide_reservation_method()
        for picking_type in self:
            if picking_type == picking_type.warehouse_id.pos_type_id:
                picking_type.hide_reservation_method = True

    @api.constrains('active')
    def _check_active(self):
        for picking_type in self:
            if picking_type.active:
                continue
            pos_config = self.env['pos.config'].sudo().search([('picking_type_id', '=', picking_type.id)], limit=1)
            if pos_config:
                raise ValidationError(_("You cannot archive '%s' as it is used by a POS configuration '%s'.", picking_type.name, pos_config.name))

class ProcurementGroup(models.Model):
    _inherit = 'procurement.group'

    pos_order_id = fields.Many2one('pos.order', 'POS Order')

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _get_new_picking_values(self):
        vals = super(StockMove, self)._get_new_picking_values()
        vals['pos_session_id'] = self.mapped('group_id.pos_order_id.session_id').id
        vals['pos_order_id'] = self.mapped('group_id.pos_order_id').id
        return vals

    def _key_assign_picking(self):
        keys = super(StockMove, self)._key_assign_picking()
        return keys + (self.group_id.pos_order_id,)

    @api.model
    def _prepare_lines_data_dict(self, order_lines):
        lines_data = defaultdict(dict)
        for product_id, olines in groupby(sorted(order_lines, key=lambda l: l.product_id.id), key=lambda l: l.product_id.id):
            lines_data[product_id].update({'order_lines': self.env['pos.order.line'].concat(*olines)})
        return lines_data

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
                ('company_id', '=', moves[0].picking_type_id.company_id.id),
                ('product_id', 'in', lines.product_id.ids),
                ('name', 'in', lots.mapped('lot_name')),
            ])
            #The previous search may return (product_id.id, lot_name) combinations that have no matching in lines.pack_lot_ids.
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
        moves_to_assign = self.filtered(lambda m: m.product_id.id not in lines_data or m.product_id.tracking == 'none'
                                                  or (not m.picking_type_id.use_existing_lots and not m.picking_type_id.use_create_lots))

        # Check for any conversion issues in the moves before setting quantities
        uoms_with_issues = set()
        for move in moves_to_assign.filtered(lambda m: m.product_uom_qty and m.product_uom != m.product_id.uom_id):
            converted_qty = move.product_uom._compute_quantity(
                move.product_uom_qty,
                move.product_id.uom_id,
                rounding_method='HALF-UP'
            )
            if not converted_qty:
                uoms_with_issues.add(
                    (move.product_uom.name, move.product_id.uom_id.name)
                )

        if uoms_with_issues:
            error_message_lines = [
                _("Conversion Error: The following unit of measure conversions result in a zero quantity due to rounding:")
            ]
            for uom_from, uom_to in uoms_with_issues:
                error_message_lines.append(_(' - From "%s" to "%s"', uom_from, uom_to))

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
        mls_qties = []
        if are_qties_done:
            for move in moves_remaining:
                move.move_line_ids.quantity = 0
                for line in lines_data[move.product_id.id]['order_lines']:
                    sum_of_lots = 0
                    for lot in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                        qty = 1 if line.product_id.tracking == 'serial' else abs(line.qty)
                        ml_vals = dict(move._prepare_move_line_vals(qty))
                        if existing_lots:
                            existing_lot = existing_lots.filtered_domain([('product_id', '=', line.product_id.id), ('name', '=', lot.lot_name)])
                            quant = self.env['stock.quant']
                            if existing_lot:
                                quant = self.env['stock.quant'].search(
                                    [('lot_id', '=', existing_lot.id), ('quantity', '>', '0.0'), ('location_id', 'child_of', move.location_id.id)],
                                    order='id desc',
                                    limit=1
                                )
                                if quant:
                                    ml_vals.update({
                                        'quant_id': quant.id,
                                    })
                                else:
                                    ml_vals.update({
                                        'lot_name': existing_lot.name,
                                    })
                        else:
                            ml_vals.update({'lot_name': lot.lot_name})
                        move_lines_to_create.append(ml_vals)
                        mls_qties.append(qty)
                        sum_of_lots += qty
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
                                continue
