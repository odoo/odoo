# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api, _
import openerp.addons.decimal_precision as dp
from openerp.exceptions import UserError

class stock_pack_details(models.TransientModel):
    _name = 'stock.pack.details'
    _description = 'Pack details'

    pack_id = fields.Many2one('stock.pack.operation', 'Pack operation')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure')
    qty_done = fields.Float('Processed Qty', digits=dp.get_precision('Product Unit of Measure'))
    quantity = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), readonly=True)
    package_id = fields.Many2one('stock.quant.package', 'Source package', domain="['|', ('location_id', 'child_of', location_id), ('location_id','=',False)]")
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    location_id = fields.Many2one('stock.location', 'Source Location', required=True)
    location_dest_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    result_package_id = fields.Many2one('stock.quant.package', 'Destination package', domain="['|', ('location_id', 'child_of', location_dest_id), ('location_id','=',False)]")
    picking_source_location_id = fields.Many2one('stock.location', related='pack_id.picking_id.location_id', readonly=True)
    picking_destination_location_id = fields.Many2one('stock.location', related='pack_id.picking_id.location_dest_id', readonly=True)

    @api.model
    def default_get(self, fields):
        res = {}
        active_id = self._context.get('active_id')
        if active_id:
            pack_op = self.env['stock.pack.operation'].browse(active_id)
            res = {
                'pack_id': pack_op.id,
                'product_id': pack_op.product_id.id,
                'product_uom_id': pack_op.product_uom_id.id,
                'quantity': pack_op.product_qty,
                'qty_done': pack_op.qty_done,
                'package_id': pack_op.package_id.id,
                'lot_id': pack_op.lot_id.id,
                'location_id': pack_op.location_id.id,
                'location_dest_id': pack_op.location_dest_id.id,
                'result_package_id': pack_op.result_package_id.id,
            }
        return res

    @api.multi
    def split_quantities(self):
        for wiz in self:
            if wiz.quantity>0.0 and wiz.qty_done < wiz.quantity:
                pack2 = self.pack_id.copy({'qty_done': 0.0, 'product_qty': wiz.quantity - wiz.qty_done})
                wiz.quantity = wiz.qty_done
                self.pack_id.write({'qty_done': wiz.qty_done, 'product_qty': wiz.quantity})
                return True
            else:
                raise UserError(_('Can not split 0 quantity'))

    @api.one
    def process(self):
        pack = self.pack_id
        pack.write({
                'product_id': self.product_id.id,
                'product_uom_id': self.product_uom_id.id,
                'qty_done': self.qty_done,
                'package_id': self.package_id.id,
                'lot_id': self.lot_id.id,
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
                'result_package_id': self.result_package_id.id,
        })
        return True