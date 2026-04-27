# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models

class PickingType(models.Model):
    _inherit = 'stock.picking.type'

    def action_mrp_overview(self):
        routing_count = self.env['stock.picking.type'].search_count([('code', '=', 'mrp_operation')])
        if routing_count == 1:
            return self.env['ir.actions.actions']._for_xml_id('mrp_workorder.action_mrp_display')
        action = self.env['ir.actions.actions']._for_xml_id('mrp_workorder.mrp_stock_picking_type_action')
        action['domain'] = [('code', '=', 'mrp_operation')]
        return action
