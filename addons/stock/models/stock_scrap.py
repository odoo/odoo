# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockScrap(models.Model):
    _name = 'stock.scrap'
    _order = 'id desc'

    def _get_default_scrap_location_id(self):
        return self.env['stock.location'].search([('scrap_location', '=', True)], limit=1).id

    def _get_default_location_id(self):
        return self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

    name = fields.Char(
        'Reference',  default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
        states={'done': [('readonly', True)]})
    origin = fields.Char(string='Source Document')
    product_id = fields.Many2one(
        'product.product', 'Product',
        required=True, states={'done': [('readonly', True)]})
    product_uom_id = fields.Many2one(
        'product.uom', 'Unit of Measure',
        required=True, states={'done': [('readonly', True)]})
    tracking = fields.Selection('Product Tracking', readonly=True, related="product_id.tracking")
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot',
        states={'done': [('readonly', True)]}, domain="[('product_id', '=', product_id)]")
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        states={'done': [('readonly', True)]})
    owner_id = fields.Many2one('res.partner', 'Owner', states={'done': [('readonly', True)]})
    move_id = fields.Many2one('stock.move', 'Scrap Move', readonly=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', states={'done': [('readonly', True)]})
    location_id = fields.Many2one(
        'stock.location', 'Location', domain="[('usage', '=', 'internal')]",
        required=True, states={'done': [('readonly', True)]}, default=_get_default_location_id)
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location', default=_get_default_scrap_location_id,
        domain="[('scrap_location', '=', True)]", states={'done': [('readonly', True)]})
    scrap_qty = fields.Float('Quantity', default=1.0, required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')], string='Status', default="draft")
    date_expected = fields.Datetime('Expected Date', default=fields.Datetime.now)

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            self.location_id = (self.picking_id.state == 'done') and self.picking_id.location_dest_id.id or self.picking_id.location_id.id

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id

    @api.model
    def create(self, vals):
        if 'name' not in vals or vals['name'] == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')
        scrap = super(StockScrap, self).create(vals)
        scrap.do_scrap()
        return scrap

    @api.multi
    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('You cannot delete a scrap which is done.'))
        return super(StockScrap, self).unlink()

    def _get_origin_moves(self):
        return self.picking_id and self.picking_id.move_lines.filtered(lambda x: x.product_id == self.product_id)

    @api.multi
    def do_scrap(self):
        for scrap in self:
            moves = scrap._get_origin_moves() or self.env['stock.move']
            move = self.env['stock.move'].create(scrap._prepare_move_values())
            quants = self.env['stock.quant'].quants_get_preferred_domain(
                move.product_qty, move,
                domain=[
                    ('qty', '>', 0),
                    ('lot_id', '=', self.lot_id.id),
                    ('package_id', '=', self.package_id.id)],
                preferred_domain_list=scrap._get_preferred_domain())
            if any([not x[0] for x in quants]):
                raise UserError(_('You cannot scrap a move without having available stock for %s. You can correct it with an inventory adjustment.') % move.product_id.name)
            self.env['stock.quant'].quants_reserve(quants, move)
            move.action_done()
            scrap.write({'move_id': move.id, 'state': 'done'})
            moves.recalculate_move_state()
        return True

    def _prepare_move_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'origin': self.origin or self.picking_id.name,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'product_uom_qty': self.scrap_qty,
            'location_id': self.location_id.id,
            'scrapped': True,
            'location_dest_id': self.scrap_location_id.id,
            'restrict_lot_id': self.lot_id.id,
            'restrict_partner_id': self.owner_id.id,
            'picking_id': self.picking_id.id
        }

    def _get_preferred_domain(self):
        if not self.picking_id:
            return []
        if self.picking_id.state == 'done':
            preferred_domain = [('history_ids', 'in', self.picking_id.move_lines.filtered(lambda x: x.state == 'done')).ids]
            preferred_domain2 = [('history_ids', 'not in', self.picking_id.move_lines.filtered(lambda x: x.state == 'done')).ids]
            return [preferred_domain, preferred_domain2]
        else:
            preferred_domain = [('reservation_id', 'in', self.picking_id.move_lines.ids)]
            preferred_domain2 = [('reservation_id', '=', False)]
            preferred_domain3 = ['&', ('reservation_id', 'not in', self.picking_id.move_lines.ids), ('reservation_id', '!=', False)]
            return [preferred_domain, preferred_domain2, preferred_domain3]

    @api.multi
    def action_get_stock_picking(self):
        action = self.env.ref('stock.action_picking_tree_all').read([])[0]
        action['domain'] = [('id', '=', self.picking_id.id)]
        return action

    @api.multi
    def action_get_stock_move(self):
        action = self.env.ref('stock.stock_move_action').read([])[0]
        action['domain'] = [('id', '=', self.move_id.id)]
        return action

    @api.multi
    def action_done(self):
        return {'type': 'ir.actions.act_window_close'}
