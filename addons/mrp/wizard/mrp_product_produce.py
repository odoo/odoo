# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models
import openerp.addons.decimal_precision as dp

class MrpProductProduce(models.TransientModel):
    _name = "mrp.product.produce"
    _description = "Record Production"

    @api.model
    def default_get(self, fields):
        res = super(MrpProductProduce, self).default_get(fields)
        if self._context and self._context.get('active_id'):
            production = self.env['mrp.production'].browse(self._context['active_id'])
            #serial_raw = production.move_raw_ids.filtered(lambda x: x.product_id.tracking == 'serial')
            serial_finished = production.move_finished_ids.filtered(lambda x: x.product_id.tracking == 'serial')
            serial = bool(serial_finished)
            if serial_finished:
                quantity = 1.0
            else:
                quantity = production.product_qty - sum(production.move_finished_ids.mapped('quantity_done'))
                quantity = quantity if (quantity > 0) else 0
            lines = []
            existing_lines = []
            for move in production.move_raw_ids.filtered(lambda x: (x.product_id.tracking != 'none') and x.state not in ('done', 'cancel')):
                if not move.move_lot_ids:
                    qty = quantity / move.bom_line_id.bom_id.product_qty * move.bom_line_id.product_qty
                    if move.product_id.tracking == 'serial':
                        while qty > 0.000001:
                            lines.append({
                                'move_id': move.id,
                                'quantity': min(1,qty),
                                'quantity_done': 0.0,
                                'plus_visible': True,
                                'product_id': move.product_id.id,
                                'production_id': production.id,
                            })
                            qty -= 1
                    else:
                        lines.append({
                            'move_id': move.id,
                            'quantity': qty,
                            'quantity_done': 0.0,
                            'plus_visible': True,
                            'product_id': move.product_id.id,
                            'production_id': production.id,
                        })
                else:
                    existing_lines += [x.id for x in move.move_lot_ids]

            res['serial'] = serial
            res['production_id'] = production.id
            res['product_qty'] = quantity
            res['product_id'] = production.product_id.id
            res['product_uom_id'] = production.product_uom_id.id
            res['consume_line_ids'] = map(lambda x: (0,0,x), lines) + map(lambda x:(4, x), existing_lines)
        return res

    serial = fields.Boolean('Requires Serial')
    production_id = fields.Many2one('mrp.production', 'Production')
    product_id = fields.Many2one('product.product', 'Product')
    product_qty = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'), required=True)
    product_uom_id = fields.Many2one('product.uom', 'Unit of Measure')
    lot_id = fields.Many2one('stock.production.lot', string='Lot')
    consume_line_ids = fields.Many2many('stock.move.lots', 'mrp_produce_stock_move_lots', string='Product to Track')
    product_tracking = fields.Selection(related="product_id.tracking")

    @api.multi
    def do_produce(self):
        # Nothing to do for lots since values are created using default data (stock.move.lots)
        moves = self.production_id.move_raw_ids + self.production_id.move_finished_ids
        for move in moves.filtered(lambda x: x.product_id.tracking == 'none' and x.state not in ('done', 'cancel')):
            quantity = self.product_qty
#             if move.bom_line_id:
#                 
#                 quantity = quantity / move.bom_line_id.bom_id.product_qty * move.bom_line_id.product_qty
            if move.unit_factor:
                move.quantity_done_store += quantity * move.unit_factor
        return {'type': 'ir.actions.act_window_close'}
