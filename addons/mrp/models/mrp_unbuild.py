# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class MrpUnbuild(models.Model):
    _name = "mrp.unbuild"
    _description = "Unbuild Order"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    def _get_default_location_id(self):
        return self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

    def _get_default_location_dest_id(self):
        return self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, states={'done': [('readonly', True)]})
    product_qty = fields.Float(
        'Quantity',
        required=True, states={'done': [('readonly', True)]})
    product_uom_id = fields.Many2one(
        'product.uom', 'Unit of Measure',
        required=True, states={'done': [('readonly', True)]})
    bom_id = fields.Many2one(
        'mrp.bom', 'Bill of Material',
        domain=[('product_tmpl_id', '=', 'product_id.product_tmpl_id')], #should be more specific
        required=True, states={'done': [('readonly', True)]})  # Add domain
    mo_id = fields.Many2one(
        'mrp.production', 'Manufacturing Order',
        domain="[('product_id', '=', product_id), ('state', 'in', ['done', 'cancel'])]",
        states={'done': [('readonly', True)]})
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot',
        domain="[('product_id', '=', product_id)]",
        states={'done': [('readonly', True)]})
    has_tracking=fields.Selection(related='product_id.tracking', readonly=True)
    location_id = fields.Many2one(
        'stock.location', 'Location',
        default=_get_default_location_id,
        required=True, states={'done': [('readonly', True)]})
    location_dest_id = fields.Many2one(
        'stock.location', 'Destination Location',
        default=_get_default_location_dest_id,
        required=True, states={'done': [('readonly', True)]})
    consume_line_ids = fields.One2many(
        'stock.move', 'consume_unbuild_id', readonly=True,
        string='Consumed Disassembly Lines')
    produce_line_ids = fields.One2many(
        'stock.move', 'unbuild_id', readonly=True,
        string='Processed Disassembly Lines')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')], string='Status', default='draft', index=True)

    @api.onchange('mo_id')
    def onchange_mo_id(self):
        if self.mo_id:
            self.product_id = self.mo_id.product_id.id
            self.product_qty = self.mo_id.product_qty

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.bom_id = self.env['mrp.bom']._bom_find(product=self.product_id)
            self.product_uom_id = self.product_id.uom_id.id

    @api.constrains('product_qty')
    def _check_qty(self):
        if self.product_qty <= 0:
            raise ValueError(_('Unbuild Order product quantity has to be strictly positive.'))

    @api.model
    def create(self, vals):
        if not vals.get('name') or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.unbuild') or _('New')
        return super(MrpUnbuild, self).create(vals)

    @api.multi
    def action_unbuild(self):
        self.ensure_one()
        if self.product_id.tracking != 'none' and not self.lot_id.id:
            raise UserError(_('Should have a lot for the finished product'))

        if self.mo_id:
            if self.mo_id.state != 'done':
                raise UserError(_('You cannot unbuild a undone manufacturing order.'))

        consume_move = self._generate_consume_moves()[0]
        produce_moves = self._generate_produce_moves()

        if any(produce_move.has_tracking != 'none' and not self.mo_id for produce_move in produce_moves):
            raise UserError(_('You should specify a manufacturing order in order to find the correct tracked products.'))

        if consume_move.has_tracking != 'none':
            self.env['stock.move.line'].create({
                'move_id': consume_move.id,
                'lot_id': self.lot_id.id,
                'qty_done': consume_move.product_uom_qty,
                'product_id': consume_move.product_id.id,
                'product_uom_id': consume_move.product_uom.id,
                'location_id': consume_move.location_id.id,
                'location_dest_id': consume_move.location_dest_id.id,
            })
        else:
            consume_move.quantity_done = consume_move.product_uom_qty
        consume_move._action_done()

        # TODO: Will fail if user do more than one unbuild with lot on the same MO. Need to check what other unbuild has aready took
        for produce_move in produce_moves:
            if produce_move.has_tracking != 'none':
                original_move = self.mo_id.move_raw_ids.filtered(lambda move: move.product_id == produce_move.product_id)
                needed_quantity = produce_move.product_qty
                for move_lines in original_move.mapped('move_line_ids').filtered(lambda ml: ml.lot_produced_id == self.lot_id):
                    # Iterate over all move_lines until we unbuilded the correct quantity.
                    taken_quantity = min(needed_quantity, move_lines.qty_done)
                    if taken_quantity:
                        self.env['stock.move.line'].create({
                            'move_id': produce_move.id,
                            'lot_id': move_lines.lot_id.id,
                            'qty_done': taken_quantity,
                            'product_id': produce_move.product_id.id,
                            'product_uom_id': move_lines.product_uom_id.id,
                            'location_id': produce_move.location_id.id,
                            'location_dest_id': produce_move.location_dest_id.id,
                        })
                        needed_quantity -= taken_quantity
            else:
                produce_move.quantity_done = produce_move.product_uom_qty
        produce_moves._action_done()
        produced_move_line_ids = produce_moves.mapped('move_line_ids').filtered(lambda ml: ml.qty_done > 0)
        consume_move.move_line_ids.write({'produce_line_ids': [(6, 0, produced_move_line_ids.ids)]})

        return self.write({'state': 'done'})

    def _generate_consume_moves(self):
        moves = self.env['stock.move']
        for unbuild in self:
            move = self.env['stock.move'].create({
                'name': unbuild.name,
                'date': unbuild.create_date,
                'product_id': unbuild.product_id.id,
                'product_uom': unbuild.product_uom_id.id,
                'product_uom_qty': unbuild.product_qty,
                'location_id': unbuild.location_id.id,
                'location_dest_id': unbuild.product_id.property_stock_production.id,
                'origin': unbuild.name,
                'consume_unbuild_id': unbuild.id,
            })
            move._action_confirm()
            moves += move
        return moves

    def _generate_produce_moves(self):
        moves = self.env['stock.move']
        for unbuild in self:
            if unbuild.mo_id:
                raw_moves = unbuild.mo_id.move_raw_ids.filtered(lambda move: move.state == 'done')
                factor = unbuild.product_qty / unbuild.mo_id.product_uom_id._compute_quantity(unbuild.mo_id.product_qty, unbuild.product_uom_id)
                for raw_move in raw_moves:
                    moves += unbuild._generate_move_from_raw_moves(raw_move, factor)
            else:
                factor = unbuild.product_uom_id._compute_quantity(unbuild.product_qty, unbuild.bom_id.product_uom_id) / unbuild.bom_id.product_qty
                boms, lines = unbuild.bom_id.explode(unbuild.product_id, factor, picking_type=unbuild.bom_id.picking_type_id)
                for line, line_data in lines:
                    moves += unbuild._generate_move_from_bom_line(line, line_data['qty'])
        return moves

    def _generate_move_from_raw_moves(self, raw_move, factor):
        return self.env['stock.move'].create({
            'name': self.name,
            'date': self.create_date,
            'product_id': raw_move.product_id.id,
            'product_uom_qty': raw_move.product_uom_qty * factor,
            'product_uom': raw_move.product_uom.id,
            'procure_method': 'make_to_stock',
            'location_dest_id': self.location_dest_id.id,
            'location_id': raw_move.location_dest_id.id,
            'unbuild_id': self.id,
        })

    def _generate_move_from_bom_line(self, bom_line, quantity):
        return self.env['stock.move'].create({
            'name': self.name,
            'date': self.create_date,
            'bom_line_id': bom_line.id,
            'product_id': bom_line.product_id.id,
            'product_uom_qty': quantity,
            'product_uom': bom_line.product_uom_id.id,
            'procure_method': 'make_to_stock',
            'location_dest_id': self.location_dest_id.id,
            'location_id': self.product_id.property_stock_production.id,
            'unbuild_id': self.id,
        })

    def action_validate(self):
        self.ensure_one()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        available_qty = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, self.lot_id, strict=True)
        if float_compare(available_qty, self.product_qty, precision_digits=precision) >= 0:
            return self.action_unbuild()
        else:
            return {
                'name': _('Insufficient Quantity'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.warn.insufficient.qty.unbuild',
                'view_id': self.env.ref('mrp.stock_warn_insufficient_qty_unbuild_form_view').id,
                'type': 'ir.actions.act_window',
                'context': {
                    'default_product_id': self.product_id.id,
                    'default_location_id': self.location_id.id,
                    'default_unbuild_id': self.id
                },
                'target': 'new'
            }
