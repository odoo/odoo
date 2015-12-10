# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import api, fields, models

import openerp.addons.decimal_precision as dp


class StockMove(models.Model):
    _inherit = 'stock.move'

    def _default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
        return self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    weight = fields.Float(compute='_cal_move_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight", default=_default_uom)

    @api.depends('product_id', 'product_uom_qty', 'product_uom')
    def _cal_move_weight(self):
        for move in self.filtered(lambda moves: moves.product_id.weight > 0.00):
            move.weight = (move.product_qty * move.product_id.weight)

    @api.multi
    def action_confirm(self):
        """
            Pass the carrier to the picking from the sales order
            (Should also work in case of Phantom BoMs when on explosion the original move is deleted)
        """
        procs_to_check = []
        for move in self:
            if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.carrier_id:
                procs_to_check += [move.procurement_id]
        res = super(StockMove, self).action_confirm()
        for proc in procs_to_check:
            pickings = (proc.move_ids.mapped('picking_id')).filtered(lambda record: not record.carrier_id)
            if pickings:
                pickings.write({
                    'carrier_id': proc.sale_line_id.order_id.carrier_id.id,
                    'carrier_price': proc.sale_line_id.order_id.delivery_price,
                })
        return res
