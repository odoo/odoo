# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpUnbuild(models.Model):
    _name = "mrp.unbuild"
    _description = "Unbuild Order"
    _inherit = ['mail.thread']
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
        help='')  # TDE: some string / help ?
    produce_line_ids = fields.One2many(
        'stock.move', 'unbuild_id', readonly=True,
        help='')  # TDE: some string / help ?
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
        if not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('mrp.unbuild') or _('New')
        unbuild = super(MrpUnbuild, self).create(vals)
        return unbuild

    @api.multi
    def action_unbuild(self):
        self.ensure_one()
        if self.product_id.tracking != 'none' and not self.lot_id.id:
            raise UserError(_('Should have a lot for the finished product'))

        consume_move = self._generate_consume_moves()[0]
        produce_moves = self._generate_produce_moves()

        # Search quants that passed production order
        qty = self.product_qty  # Convert to qty on product UoM
        if self.mo_id:
            finished_moves = self.mo_id.move_finished_ids.filtered(lambda move: move.product_id == self.mo_id.product_id)
            domain = [('qty', '>', 0), ('history_ids', 'in', finished_moves.ids)]
        else:
            domain = [('qty', '>', 0)]
        quants = self.env['stock.quant'].quants_get_preferred_domain(
            qty, consume_move,
            domain=domain,
            preferred_domain_list=[],
            lot_id=self.lot_id.id)
        self.env['stock.quant'].quants_reserve(quants, consume_move)

        if consume_move.has_tracking != 'none':
            if not quants[0][0]:
                raise UserError(_("You don't have in the stock the lot %s.") % (self.lot_id.name,))
            self.env['stock.move.lots'].create({
                'move_id': consume_move.id,
                'lot_id': self.lot_id.id,
                'quantity_done': consume_move.product_uom_qty,
                'quantity': consume_move.product_uom_qty})
        else:
            consume_move.quantity_done = consume_move.product_uom_qty
        consume_move.move_validate()
        original_quants = consume_move.quant_ids.mapped('consumed_quant_ids')

        for produce_move in produce_moves:
            if produce_move.has_tracking != 'none':
                original = original_quants.filtered(lambda quant: quant.product_id == produce_move.product_id)
                if not original:
                    raise UserError(_("You don't have in the stock the required lot/serial number for %s .") % (produce_move.product_id.name,))
                quantity_todo = produce_move.product_qty
                for quant in original:
                    if quantity_todo <= 0:
                        break
                    move_quantity = min(quantity_todo, quant.qty)
                    self.env['stock.move.lots'].create({
                        'move_id': produce_move.id,
                        'lot_id': quant.lot_id.id,
                        'quantity_done': produce_move.product_id.uom_id._compute_quantity(move_quantity, produce_move.product_uom),
                        'quantity': produce_move.product_id.uom_id._compute_quantity(move_quantity, produce_move.product_uom),
                    })
                    quantity_todo -= move_quantity
            else:
                produce_move.quantity_done = produce_move.product_uom_qty
        produce_moves.move_validate()
        produced_quant_ids = produce_moves.mapped('quant_ids').filtered(lambda quant: quant.qty > 0)
        consume_move.quant_ids.sudo().write({'produced_quant_ids': [(6, 0, produced_quant_ids.ids)]})

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
            move.action_confirm()
            moves += move
        return moves

    def _generate_produce_moves(self):
        moves = self.env['stock.move']
        for unbuild in self:
            factor = unbuild.product_uom_id._compute_quantity(unbuild.product_qty, unbuild.bom_id.product_uom_id) / unbuild.bom_id.product_qty
            boms, lines = unbuild.bom_id.explode(unbuild.product_id, factor, picking_type=unbuild.bom_id.picking_type_id)
            for line, line_data in lines:
                moves += unbuild._generate_move_from_bom_line(line, line_data['qty'])
        return moves

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
