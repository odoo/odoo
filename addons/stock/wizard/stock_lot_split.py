# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

class stock_lot_split(models.TransientModel):
    _name = 'stock.lot.split'
    _description = 'Lot split'

    @api.one
    @api.depends('line_ids')
    def _compute_qty_done(self):
        self.qty_done = sum([x.product_qty for x in self.line_ids])

    pack_id = fields.Many2one('stock.pack.operation', 'Pack operation')
    product_qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    product_id = fields.Many2one('product.product', 'Product', readonly=True)
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure', readonly=True)
    line_ids = fields.One2many('stock.lot.split.line', 'split_id')
    qty_done = fields.Float('Processed Qty', digits=dp.get_precision('Product Unit of Measure'), compute='_compute_qty_done')
    picking_type_id = fields.Many2one('stock.picking.type', related='pack_id.picking_id.picking_type_id')

    @api.multi
    def process(self):
        self.ensure_one()
        if not self.line_ids:
            raise UserError (_('Please provide at least one line'))
        # Split pack operations
        firstline = True
        totals_other = 0.0
        for line in self.line_ids:
            if not line.lot_name and not line.lot_id:
                raise UserError(_('Please provide a lot/serial number for every line'))
            # In case of only creating lots, we will have the text in lot_name, otherwise the lot_id
            if line.lot_name:
                if self.pack_id.lot_id and line.lot_name == self.pack_id.lot_id.name:
                    lot = self.pack_id.lot_id
                else:
                    lot = self.env['stock.production.lot'].create({'name': line.lot_name, 'product_id': self.pack_id.product_id.id})
            else:
                lot = line.lot_id
            if firstline:
                self.pack_id.write({'lot_id': lot.id,
                                   'qty_done': line.product_qty})
                firstline = False
            else:
                pack_new = self.pack_id.copy()
                pack_new.write({'lot_id': lot.id,
                                'qty_done': line.product_qty,
                                'product_qty': line.product_qty})
                totals_other += line.product_qty
        old_qty = self.pack_id.product_qty
        if old_qty - totals_other > 0:
            self.pack_id.product_qty = self.pack_id.product_qty - totals_other
        else:
            self.pack_id.product_qty = 0.0

        return True


class stock_lot_split_line(models.TransientModel):
    _name = 'stock.lot.split.line'
    _description = 'Lot split line'

    split_id = fields.Many2one('stock.lot.split')
    lot_id = fields.Many2one('stock.production.lot', string="Lot/Serial Number")
    lot_name = fields.Char('Name')
    product_qty = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), default=1.0)