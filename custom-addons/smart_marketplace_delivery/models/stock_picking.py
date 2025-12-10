# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    sha6er_shipment_ids = fields.One2many('sha6er.shipment', 'picking_id', string='Sha6er Shipments')
    sha6er_shipment_count = fields.Integer(string='Sha6er Shipment Count', compute='_compute_sha6er_shipment_count')
    
    def _compute_sha6er_shipment_count(self):
        for picking in self:
            picking.sha6er_shipment_count = len(picking.sha6er_shipment_ids)
    
    def action_create_sha6er_shipment(self):
        """Create Sha6er shipment for this picking"""
        self.ensure_one()
        if self.sha6er_shipment_ids:
            # Return existing shipment
            return {
                'type': 'ir.actions.act_window',
                'name': 'Sha6er Shipment',
                'res_model': 'sha6er.shipment',
                'res_id': self.sha6er_shipment_ids[0].id,
                'view_mode': 'form',
            }
        
        shipment = self.env['sha6er.shipment'].create({
            'picking_id': self.id,
        })
        shipment.action_create_shipment()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Sha6er Shipment',
            'res_model': 'sha6er.shipment',
            'res_id': shipment.id,
            'view_mode': 'form',
        }

