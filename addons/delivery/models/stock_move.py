# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from openerp import models, fields, api
import openerp.addons.decimal_precision as dp

class StockMove(models.Model):
    _inherit = 'stock.move'

    def _default_uom(self):
        uom_categ_id = self.env.ref('product.product_uom_categ_kgm').id
        return self.env['product.uom'].search([('category_id', '=', uom_categ_id), ('factor', '=', 1)], limit=1)

    weight = fields.Float(compute='_cal_move_weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_net = fields.Float(compute='_cal_move_weight', string='Net weight', digits=dp.get_precision('Stock Weight'), store=True)
    weight_uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True, readonly=True, help="Unit of Measure (Unit of Measure) is the unit of measurement for Weight", default=_default_uom)

    @api.depends('product_id')
    def _cal_move_weight(self):
        for move in self.filtered(lambda moves: moves.product_id.weight > 0.00):
            weight = weight_net = 0.00
            converted_qty = move.product_qty
            weight = (converted_qty * move.product_id.weight)

            if move.product_id.weight_net > 0.00:
                weight_net = (converted_qty * move.product_id.weight_net)

            move.weight = weight
            move.weight_net = weight_net

    @api.multi
    def action_confirm(self):
        """
            Pass the carrier to the picking from the sales order
            (Should also work in case of Phantom BoMs when on explosion the
                original move is deleted)
        """
        procs_to_check = []
        for move in self:
            if move.procurement_id and move.procurement_id.sale_line_id and move.procurement_id.sale_line_id.order_id.carrier_id:
                procs_to_check += [move.procurement_id]
        res = super(StockMove, self).action_confirm()
        StockPiking = self.env["stock.picking"]
        for proc in procs_to_check:
            pickings = list(set([x.picking_id.id for x in proc.move_ids if x.picking_id and not x.picking_id.carrier_id]))
            if pickings:
                StockPiking.write({'carrier_id': proc.sale_line_id.order_id.carrier_id.id})
        return res
