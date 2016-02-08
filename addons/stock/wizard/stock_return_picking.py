# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
import odoo.addons.decimal_precision as dp
from odoo.exceptions import UserError


class StockReturnPickingLine(models.TransientModel):
    _name = "stock.return.picking.line"
    _rec_name = 'product_id'

    product_id = fields.Many2one('product.product', string="Product", required=True)
    quantity = fields.Float(string="Quantity", digits_compute=dp.get_precision('Product Unit of Measure'), required=True)
    wizard_id = fields.Many2one('stock.return.picking', string="Wizard")
    move_id = fields.Many2one('stock.move', string="Move")


class StockReturnPicking(models.TransientModel):
    _name = 'stock.return.picking'
    _description = 'Return Picking'

    product_return_moves = fields.One2many('stock.return.picking.line', 'wizard_id', string='Moves')
    move_dest_exists = fields.Boolean('Chained Move Exists', readonly=True, help="Technical field used to hide help tooltip if not needed")
    original_location_id = fields.Many2one('stock.location')
    parent_location_id = fields.Many2one('stock.location')
    location_id = fields.Many2one('stock.location', string='Return Location', domain="['|', ('id', '=', original_location_id), '&', ('return_location', '=', True), ('id', 'child_of', parent_location_id)]")

    @api.model
    def default_get(self, fields):
        """
         To get default values for the object.
         @param self: The object pointer.
         @return: A dictionary with default values for all field in ``fields``
        """
        result1 = []
        if self.env.context and self.env.context.get('active_ids', False):
            if len(self.env.context.get('active_ids')) > 1:
                raise UserError(_('Warning!'), _("You may only return one picking at a time!"))
        res = super(StockReturnPicking, self).default_get(fields)
        record_id = self.env.context and self.env.context.get('active_id') or False
        # record_id = ctx_active_id and ctx_active_id or False
        StockPicking = self.env['stock.picking']
        picking = StockPicking.browse(record_id)
        Quant = self.env["stock.quant"]
        chained_move_exist = False
        if picking:
            if picking.state != 'done':
                raise UserError(_("You may only return pickings that are Done!"))

            for move in picking.move_lines:
                if move.move_dest_id:
                    chained_move_exist = True
                #  Sum the quants in that location that can be returned (they should have been moved by the moves that were included in the returned picking)
                qty = 0
                quant_search = Quant.search([('history_ids', 'in', move.id), ('qty', '>', 0.0), ('location_id', 'child_of', move.location_dest_id.id)])
                for quant in quant_search:
                    if not quant.reservation_id or quant.reservation_id.origin_returned_move_id.id != move.id:
                        qty += quant.qty
                qty = move.product_id.uom_id._compute_qty(qty, move.product_uom.id)
                result1.append((0, 0, {'product_id': move.product_id.id, 'quantity': qty, 'move_id': move.id}))

            if len(result1) == 0:
                raise UserError(_("No products to return (only lines in Done state and not fully returned yet can be returned)!"))
            if 'product_return_moves' in fields:
                res.update({'product_return_moves': result1})
            if 'move_dest_exists' in fields:
                res.update({'move_dest_exists': chained_move_exist})
            if 'parent_location_id' in fields and picking.location_id.usage == 'internal':
                res.update({'parent_location_id': picking.picking_type_id.warehouse_id and picking.picking_type_id.warehouse_id.view_location_id.id or picking.location_id.location_id.id})
            if 'original_location_id' in fields:
                res.update({'original_location_id': picking.location_id.id})
            if 'location_id' in fields:
                res.update({'location_id': picking.location_id.id})
        return res

    @api.multi
    def _create_returns(self):
        record_id = self.env.context.get('active_id', False)
        StockMove = self.env['stock.move']
        StockPicking = self.env['stock.picking']
        picking = StockPicking.browse(record_id)
        data = self[0]
        returned_lines = 0
        moves_to_unreserve = self.env['stock.move']

        # Cancel assignment of existing chained assigned moves
        for move in picking.move_lines:
            to_check_moves = [move.move_dest_id] if move.move_dest_id.id else []
            while to_check_moves:
                current_move = to_check_moves.pop()
                if current_move.state not in ('done', 'cancel') and current_move.reserved_quant_ids:
                    moves_to_unreserve |= current_move
                split_move = StockMove.search([('split_from', '=', current_move.id)])
                if split_move:
                    to_check_moves += split_move

        if moves_to_unreserve:
            moves_to_unreserve.do_unreserve()
            # break the link between moves in order to be able to fix them later if needed
            moves_to_unreserve.write({'move_orig_ids': False})

        # Create new picking for returned products
        pick_type_id = picking.picking_type_id.return_picking_type_id and picking.picking_type_id.return_picking_type_id.id or picking.picking_type_id.id
        new_picking = picking.copy({
            'move_lines': [],
            'picking_type_id': pick_type_id,
            'state': 'draft',
            'origin': picking.name,
            'location_id': picking.location_dest_id.id,
            'location_dest_id': data.location_id and data.location_id.ids[0] or picking.location_id.id,
        })

        for data_get in data.product_return_moves:
            move = data_get.move_id
            if not move:
                raise UserError(_("You have manually created product lines, please delete them to proceed"))
            new_qty = data_get.quantity
            if new_qty:
                # The return of a return should be linked with the original's destination move if it was not cancelled
                if move.origin_returned_move_id.move_dest_id.id and move.origin_returned_move_id.move_dest_id.state != 'cancel':
                    move_dest_id = move.origin_returned_move_id.move_dest_id.id
                else:
                    move_dest_id = False

                returned_lines += 1
                location_id = data.location_id and data.location_id.ids[0] or move.location_id.id
                move.copy({
                    'product_id': data_get.product_id.id,
                    'product_uom_qty': new_qty,
                    'picking_id': new_picking.id,
                    'state': 'draft',
                    'location_id': move.location_dest_id.id,
                    'location_dest_id': location_id,
                    'picking_type_id': pick_type_id,
                    'warehouse_id': picking.picking_type_id.warehouse_id.id,
                    'origin_returned_move_id': move.id,
                    'procure_method': 'make_to_stock',
                    'move_dest_id': move_dest_id,
                })

        if not returned_lines:
            raise UserError(_("Please specify at least one non-zero quantity."))

        new_picking.action_confirm()
        new_picking.action_assign()
        return new_picking.id, pick_type_id

    @api.multi
    def create_returns(self):
        """
         Creates return picking and returns act_window to new picking
        """
        new_picking_id, pick_type_id = self._create_returns()
        # Override the context to disable all the potential filters that could have been set previously
        ctx = self.env.context.copy()
        ctx.update({
            'search_default_picking_type_id': pick_type_id,
            'search_default_draft': False,
            'search_default_assigned': False,
            'search_default_confirmed': False,
            'search_default_ready': False,
            'search_default_late': False,
            'search_default_available': False,
        })
        return {
            'name': _('Returned Picking'),
            'view_type': 'form',
            'view_mode': 'form,tree,calendar',
            'res_model': 'stock.picking',
            'res_id': new_picking_id,
            'type': 'ir.actions.act_window',
            'context': ctx,
        }
