# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class MrpMpsForecastDetails(models.TransientModel):
    _name = "mrp.mps.forecast.details"
    _description = "Forecast Demand Details"

    move_ids = fields.Many2many('stock.move', readonly=True)
    purchase_order_line_ids = fields.Many2many('purchase.order.line', readonly=True)

    rfq_qty = fields.Integer('Quantity from RFQ', compute='_compute_quantity')
    moves_qty = fields.Integer('Quantity from Incoming Moves',
        compute='_compute_quantity')
    manufacture_qty = fields.Integer('Quantity from Manufacturing Order',
        compute='_compute_quantity')
    total_qty = fields.Integer('Actual Replenishment', compute='_compute_quantity')

    @api.depends('move_ids', 'purchase_order_line_ids')
    def _compute_quantity(self):
        for mps in self:
            mps.moves_qty = sum(mps.move_ids.filtered(lambda m: m.picking_id).mapped('product_qty'))
            mps.manufacture_qty = sum(mps.move_ids.filtered(lambda m: m.production_id).mapped('product_qty'))
            mps.rfq_qty = sum([l.product_uom._compute_quantity(l.product_qty, l.product_id.uom_id) for l in mps.purchase_order_line_ids])
            mps.total_qty = mps.moves_qty + mps.manufacture_qty + mps.rfq_qty

    def action_open_rfq_details(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': self.env.context.get('action_name'),
            'domain': [('id', 'in', self.purchase_order_line_ids.mapped('order_id').ids)],
            'context': {
                'quotation_only': True,
            }
        }

    def action_open_mo_details(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': self.env.context.get('action_name'),
            'domain': [('id', 'in', self.move_ids.mapped('production_id').ids)],
        }

    def action_open_incoming_moves_details(self):
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'views': [(False, 'list'), (False, 'form')],
            'view_mode': 'list,form',
            'target': 'current',
            'name': self.env.context.get('action_name'),
            'domain': [('id', 'in', self.move_ids.mapped('picking_id').ids)],
        }
