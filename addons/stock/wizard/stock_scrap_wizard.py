# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from odoo.tools import float_compare


class StockScrapWizard(models.TransientModel):
    _name = 'stock.scrap.wizard'
    _description = 'Scrap'

    def _get_default_scrap_location_id(self):
        return self.env['stock.location'].search([('scrap_location', '=', True)], limit=1).id

    def _get_default_location_id(self):
        return self.env.ref('stock.stock_location_stock', raise_if_not_found=False)

    product_id = fields.Many2one('product.product', 'Product', required=True)
    scrap_qty = fields.Float('Quantity', default=1.0, required=True)
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure', required=True)
    lot_id = fields.Many2one('stock.production.lot', 'Lot', domain="[('product_id', '=', product_id)]")
    package_id = fields.Many2one('stock.quant.package', 'Package')
    owner_id = fields.Many2one('res.partner', 'Owner')
    location_id = fields.Many2one(
        'stock.location', 'Location', domain="[('usage', '=', 'internal')]", required=True, default=_get_default_location_id)
    scrap_location_id = fields.Many2one('stock.location', 'Scrap Location', default=_get_default_scrap_location_id, domain="[('scrap_location', '=', True)]", required=True)
    picking_id = fields.Many2one('stock.picking', 'Picking')
    tracking = fields.Selection('Product Tracking', related="product_id.tracking")
    quants = fields.Many2many('stock.quant', compute='_compute_quants', store=True)
    origin = fields.Char(string='Source Document')
    scrap_id = fields.Many2one('stock.scrap', 'Scrap')

    @api.one
    @api.depends('product_id')
    def _compute_quants(self):
        for quant in self.env['stock.quant'].search([('product_id', '=', self.product_id.id), ('location_id.usage', '=', 'internal')]):
            self.quants = [(6, 0, [quant.id])]

    @api.onchange('picking_id')
    def onchange_picking_id(self):
        if self.picking_id:
            self.location_id = (self.picking_id.state == 'done') and self.picking_id.location_dest_id.id or self.picking_id.location_id.id

    @api.onchange('product_id')
    def onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id

    def _prepare_scrap_vals(self):
        return {
            'product_id': self.product_id,
            'scrap_qty': self.scrap_qty,
            'origin': self.origin,
            'product_id': self.product_id.id,
            'product_uom_id': self.product_uom_id.id,
            'location_id': self.location_id.id,
            'scrap_location_id': self.scrap_location_id.id,
            'lot_id': self.lot_id.id,
            'picking_id': self.picking_id.id,
            'package_id': self.package_id.id,
            }

    def do_scrap(self):
        scrap = self.scrap_id
        if not scrap:
            scrap = self.env['stock.scrap'].create(self._prepare_scrap_vals())
        return scrap.do_scrap()

    def action_done(self):
        self.ensure_one()
        self.do_scrap()
        return True

    def get_action(self):
        """Will return the action to open warning wizard"""
        action = self.env.ref('stock.action_stock_scrap_warning_wizard').read()[0]
        action['res_id'] = self.id
        return action

    def action_validate(self):
        """Checks and do scrap if given qty is available in stock else will call get_action """
        self.ensure_one()
        lot_id = self.lot_id or None
        package_id = self.package_id or None
        owner_id = self.owner_id or None
        available_qty = self.env['stock.quant']._get_available_quantity(self.product_id, self.location_id, lot_id, package_id, owner_id, strict=True)
        if float_compare(available_qty, self.scrap_qty, 2) >= 0:
            self.do_scrap()
        else:
            return self.get_action()
        return True
