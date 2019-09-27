# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools import float_compare


class StockScrap(models.Model):
    _name = 'stock.scrap'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _description = 'Scrap'

    def _get_default_scrap_location_id(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        return self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [company_id, False])], limit=1).id

    def _get_default_location_id(self):
        company_id = self.env.context.get('default_company_id') or self.env.company.id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        return None

    name = fields.Char(
        'Reference',  default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
        states={'done': [('readonly', True)]})
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, required=True, states={'done': [('readonly', True)]})
    origin = fields.Char(string='Source Document')
    product_id = fields.Many2one(
        'product.product', 'Product', domain="[('type', 'in', ['product', 'consu']), '|', ('company_id', '=', False), ('company_id', '=', company_id)]",
        required=True, states={'done': [('readonly', True)]}, check_company=True)
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
        required=True, states={'done': [('readonly', True)]}, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    tracking = fields.Selection('Product Tracking', readonly=True, related="product_id.tracking")
    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot/Serial',
        states={'done': [('readonly', True)]}, domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        states={'done': [('readonly', True)]}, check_company=True)
    owner_id = fields.Many2one('res.partner', 'Owner', states={'done': [('readonly', True)]}, check_company=True)
    move_id = fields.Many2one('stock.move', 'Scrap Move', readonly=True, check_company=True)
    picking_id = fields.Many2one('stock.picking', 'Picking', states={'done': [('readonly', True)]}, check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location', domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]",
        required=True, states={'done': [('readonly', True)]}, default=_get_default_location_id, check_company=True)
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location', default=_get_default_scrap_location_id,
        domain="[('scrap_location', '=', True), ('company_id', 'in', [company_id, False])]", required=True, states={'done': [('readonly', True)]}, check_company=True)
    scrap_qty = fields.Float('Quantity', default=1.0, required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')],
        string='Status', default="draft", readonly=True, tracking=True)
    date_done = fields.Datetime('Date', readonly=True)

    @api.onchange('picking_id')
    def _onchange_picking_id(self):
        if self.picking_id:
            self.location_id = (self.picking_id.state == 'done') and self.picking_id.location_dest_id.id or self.picking_id.location_id.id

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            if self.tracking == 'serial':
                self.scrap_qty = 1
            self.product_uom_id = self.product_id.uom_id.id
            # Check if we can get a more precise location instead of
            # the default location (a location corresponding to where the
            # reserved product is stored)
            if self.picking_id:
                for move_line in self.picking_id.move_line_ids:
                    if move_line.product_id == self.product_id:
                        self.location_id = move_line.location_id if move_line.state != 'done' else move_line.location_dest_id
                        break

    @api.onchange('company_id')
    def _onchange_company_id(self):
        if self.company_id:
            warehouse = self.env['stock.warehouse'].search([('company_id', '=', self.company_id.id)], limit=1)
            self.location_id = warehouse.lot_stock_id
            self.scrap_location_id = self.env['stock.location'].search([
                ('scrap_location', '=', True),
                ('company_id', 'in', [self.company_id.id, False]),
            ], limit=1)
        else:
            self.location_id = False
            self.scrap_location_id = False

    def unlink(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('You cannot delete a scrap which is done.'))
        return super(StockScrap, self).unlink()

    def _get_origin_moves(self):
        return self.picking_id and self.picking_id.move_lines.filtered(lambda x: x.product_id == self.product_id)

    def _prepare_move_values(self):
        self.ensure_one()
        location_id = self.location_id.id
        if self.picking_id and self.picking_id.picking_type_code == 'incoming':
            location_id = self.picking_id.location_dest_id.id
        return {
            'name': self.name,
            'origin': self.origin or self.picking_id.name or self.name,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'state': 'draft',
            'product_uom_qty': self.scrap_qty,
            'location_id': location_id,
            'scrapped': True,
            'location_dest_id': self.scrap_location_id.id,
            'move_line_ids': [(0, 0, {'product_id': self.product_id.id,
                                           'product_uom_id': self.product_uom_id.id, 
                                           'qty_done': self.scrap_qty,
                                           'location_id': location_id,
                                           'location_dest_id': self.scrap_location_id.id,
                                           'package_id': self.package_id.id, 
                                           'owner_id': self.owner_id.id,
                                           'lot_id': self.lot_id.id, })],
#             'restrict_partner_id': self.owner_id.id,
            'picking_id': self.picking_id.id
        }

    def do_scrap(self):
        self._check_company()
        for scrap in self:
            scrap.name = self.env['ir.sequence'].next_by_code('stock.scrap') or _('New')
            move = self.env['stock.move'].create(scrap._prepare_move_values())
            # master: replace context by cancel_backorder
            move.with_context(is_scrap=True)._action_done()
            scrap.write({'move_id': move.id, 'state': 'done'})
            scrap.date_done = fields.Datetime.now()
        return True

    def action_get_stock_picking(self):
        action = self.env.ref('stock.action_picking_tree_all').read([])[0]
        action['domain'] = [('id', '=', self.picking_id.id)]
        return action

    def action_get_stock_move_lines(self):
        action = self.env.ref('stock.stock_move_line_action').read([])[0]
        action['domain'] = [('move_id', '=', self.move_id.id)]
        return action

    def action_validate(self):
        self.ensure_one()
        if self.product_id.type != 'product':
            return self.do_scrap()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        location_id = self.location_id
        if self.picking_id and self.picking_id.picking_type_code == 'incoming':
            location_id = self.picking_id.location_dest_id
        available_qty = sum(self.env['stock.quant']._gather(self.product_id,
                                                            location_id,
                                                            self.lot_id,
                                                            self.package_id,
                                                            self.owner_id,
                                                            strict=True).mapped('quantity'))
        scrap_qty = self.product_uom_id._compute_quantity(self.scrap_qty, self.product_id.uom_id)
        if float_compare(available_qty, scrap_qty, precision_digits=precision) >= 0:
            return self.do_scrap()
        else:
            ctx = dict(self.env.context)
            ctx.update({
                'default_product_id': self.product_id.id,
                'default_location_id': self.location_id.id,
                'default_scrap_id': self.id
            })
            return {
                'name': _('Insufficient Quantity'),
                'view_mode': 'form',
                'res_model': 'stock.warn.insufficient.qty.scrap',
                'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            }

