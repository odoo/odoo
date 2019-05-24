# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.tools import float_compare


class StockCreateScrap(models.TransientModel):
    _name = 'stock.create.scrap'

    def _get_default_scrap_location_id(self):
        return self.env['stock.location'].search([('scrap_location', '=', True), ('company_id', 'in', [self.env.company_id.id, False])], limit=1).id

    def _get_default_location_id(self):
        company_user = self.env.company_id
        warehouse = self.env['stock.warehouse'].search([('company_id', '=', company_user.id)], limit=1)
        if warehouse:
            return warehouse.lot_stock_id.id
        return None

    name = fields.Char(
        'Reference',  default=lambda self: _('New'),
        copy=False, readonly=True, required=True,
        states={'done': [('readonly', True)]})
    product_id = fields.Many2one(
        'product.product', 'Product', domain=[('type', 'in', ['product', 'consu'])],
        required=True, states={'done': [('readonly', True)]})
    product_uom_id = fields.Many2one(
        'uom.uom', 'Unit of Measure',
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
        domain="[('scrap_location', '=', True)]", required=True, states={'done': [('readonly', True)]})
    scrap_qty = fields.Float('Quantity', default=1.0, required=True, states={'done': [('readonly', True)]})
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done')], string='Status', default="draft")
    quant_ids = fields.Many2many('stock.quant', compute='_compute_quant_ids')

    @api.one
    @api.depends('product_id')
    def _compute_quant_ids(self):
        self.quant_ids = self.env['stock.quant'].search([
            ('product_id', '=', self.product_id.id),
            ('location_id.usage', '=', 'internal')
        ])

    def create_and_do_scrap(self):
        self.env.cr.execute('select * from stock_create_scrap where id = %s' % self.id)
        vals = self.env.cr.dictfetchall()
        scrap = self.env['stock.scrap'].create(vals)
        return scrap.do_scrap()

    def action_validate(self):
        self.ensure_one()
        if self.product_id.type != 'product':
            return self.create_and_do_scrap()
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        available_qty = sum(self.env['stock.quant']._gather(self.product_id,
                                                            self.location_id,
                                                            self.lot_id,
                                                            self.package_id,
                                                            self.owner_id,
                                                            strict=True).mapped('quantity'))
        scrap_qty = self.product_uom_id._compute_quantity(self.scrap_qty, self.product_id.uom_id)
        if float_compare(available_qty, scrap_qty, precision_digits=precision) >= 0:
            return self.create_and_do_scrap()
        else:
            return {
                'name': _('Insufficient Quantity'),
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'stock.create.scrap',
                'view_id': self.env.ref('stock.stock_warn_insufficient_qty_form_view').id,
                'type': 'ir.actions.act_window',
                'res_id': self.id,
                'target': 'new'
            }

    def action_done(self):
        return self.create_and_do_scrap()

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            # Check if we can get a more precise location instead of
            # the default location (a location corresponding to where the
            # reserved product is stored)
            if self.picking_id:
                for move_line in self.picking_id.move_line_ids:
                    if move_line.product_id == self.product_id:
                        self.location_id = move_line.location_id
                        break
