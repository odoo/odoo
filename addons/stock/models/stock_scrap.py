# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, float_is_zero


class StockScrap(models.Model):
    _name = 'stock.scrap'
    _inherit = ['mail.thread']
    _order = 'id desc'
    _description = 'Scrap'

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
        compute="_compute_product_uom_id", store=True, readonly=False, precompute=True,
        required=True, states={'done': [('readonly', True)]}, domain="[('category_id', '=', product_uom_category_id)]")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id')
    tracking = fields.Selection(string='Product Tracking', readonly=True, related="product_id.tracking")
    lot_id = fields.Many2one(
        'stock.lot', 'Lot/Serial',
        states={'done': [('readonly', True)]}, domain="[('product_id', '=', product_id), ('company_id', '=', company_id)]", check_company=True)
    package_id = fields.Many2one(
        'stock.quant.package', 'Package',
        states={'done': [('readonly', True)]}, check_company=True)
    owner_id = fields.Many2one('res.partner', 'Owner', states={'done': [('readonly', True)]}, check_company=True)
    move_id = fields.Many2one('stock.move', 'Scrap Move', readonly=True, check_company=True, copy=False)
    picking_id = fields.Many2one('stock.picking', 'Picking', states={'done': [('readonly', True)]}, check_company=True)
    location_id = fields.Many2one(
        'stock.location', 'Source Location',
        compute='_compute_location_id', store=True, required=True, precompute=True, states={'done': [('readonly', True)]},
        domain="[('usage', '=', 'internal'), ('company_id', 'in', [company_id, False])]", check_company=True, readonly=False)
    scrap_location_id = fields.Many2one(
        'stock.location', 'Scrap Location',
        compute='_compute_scrap_location_id', store=True, required=True, precompute=True, states={'done': [('readonly', True)]},
        domain="[('scrap_location', '=', True), ('company_id', 'in', [company_id, False])]", check_company=True, readonly=False)
    scrap_qty = fields.Float(
        'Quantity', required=True, states={'done': [('readonly', True)]}, digits='Product Unit of Measure',
        compute='_compute_scrap_qty', precompute=True, readonly=False, store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')],
        string='Status', default="draft", readonly=True, tracking=True)
    date_done = fields.Datetime('Date', readonly=True)

    @api.depends('product_id')
    def _compute_product_uom_id(self):
        for scrap in self:
            scrap.product_uom_id = scrap.product_id.uom_id

    @api.depends('company_id', 'picking_id')
    def _compute_location_id(self):
        groups = self.env['stock.warehouse']._read_group(
            [('company_id', 'in', self.company_id.ids)], ['company_id'], ['lot_stock_id:array_agg'])
        locations_per_company = {
            company.id: lot_stock_ids[0] if lot_stock_ids else False
            for company, lot_stock_ids in groups
        }
        for scrap in self:
            if scrap.picking_id:
                scrap.location_id = scrap.picking_id.location_dest_id if scrap.picking_id.state == 'done' else scrap.picking_id.location_id
            else:
                scrap.location_id = locations_per_company[scrap.company_id.id]

    @api.depends('company_id')
    def _compute_scrap_location_id(self):
        groups = self.env['stock.location']._read_group(
            [('company_id', 'in', self.company_id.ids), ('scrap_location', '=', True)], ['company_id'], ['id:min'])
        locations_per_company = {
            company.id: stock_warehouse_id
            for company, stock_warehouse_id in groups
        }
        for scrap in self:
            scrap.scrap_location_id = locations_per_company[scrap.company_id.id]

    @api.depends('move_id', 'move_id.move_line_ids.qty_done', 'product_id')
    def _compute_scrap_qty(self):
        self.scrap_qty = 1
        for scrap in self:
            if scrap.move_id:
                scrap.scrap_qty = scrap.move_id.quantity_done

    @api.onchange('lot_id')
    def _onchange_serial_number(self):
        if self.product_id.tracking == 'serial' and self.lot_id:
            message, recommended_location = self.env['stock.quant']._check_serial_number(self.product_id,
                                                                                         self.lot_id,
                                                                                         self.company_id,
                                                                                         self.location_id,
                                                                                         self.picking_id.location_dest_id)
            if message:
                if recommended_location:
                    self.location_id = recommended_location
                return {'warning': {'title': _('Warning'), 'message': message}}

    @api.ondelete(at_uninstall=False)
    def _unlink_except_done(self):
        if 'done' in self.mapped('state'):
            raise UserError(_('You cannot delete a scrap which is done.'))

    def _prepare_move_values(self):
        self.ensure_one()
        return {
            'name': self.name,
            'origin': self.origin or self.picking_id.name or self.name,
            'company_id': self.company_id.id,
            'product_id': self.product_id.id,
            'product_uom': self.product_uom_id.id,
            'state': 'draft',
            'product_uom_qty': self.scrap_qty,
            'location_id': self.location_id.id,
            'scrapped': True,
            'location_dest_id': self.scrap_location_id.id,
            'move_line_ids': [(0, 0, {'product_id': self.product_id.id,
                                           'product_uom_id': self.product_uom_id.id, 
                                           'qty_done': self.scrap_qty,
                                           'location_id': self.location_id.id,
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
        action = self.env['ir.actions.act_window']._for_xml_id('stock.action_picking_tree_all')
        action['domain'] = [('id', '=', self.picking_id.id)]
        return action

    def action_get_stock_move_lines(self):
        action = self.env['ir.actions.act_window']._for_xml_id('stock.stock_move_line_action')
        action['domain'] = [('move_id', '=', self.move_id.id)]
        return action

    def action_validate(self):
        self.ensure_one()
        if float_is_zero(self.scrap_qty,
                         precision_rounding=self.product_uom_id.rounding):
            raise UserError(_('You can only enter positive quantities.'))
        if self.product_id.type != 'product':
            return self.do_scrap()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        available_qty = sum(self.env['stock.quant']._gather(self.product_id,
                                                            self.location_id,
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
                'default_scrap_id': self.id,
                'default_quantity': scrap_qty,
                'default_product_uom_name': self.product_id.uom_name
            })
            return {
                'name': self.product_id.display_name + _(': Insufficient Quantity To Scrap'),
                'view_mode': 'form',
                'res_model': 'stock.warn.insufficient.qty.scrap',
                'view_id': self.env.ref('stock.stock_warn_insufficient_qty_scrap_form_view').id,
                'type': 'ir.actions.act_window',
                'context': ctx,
                'target': 'new'
            }
