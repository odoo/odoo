# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[('mrp_operation', 'Manufacturing Operation')])
    count_mo_todo = fields.Integer(compute='_get_mo_count')
    count_mo_waiting = fields.Integer(compute='_get_mo_count')
    count_mo_late = fields.Integer(compute='_get_mo_count')

    def _get_mo_count(self):
        mrp_picking_types = self.filtered(lambda picking: picking.code == 'mrp_operation')
        if not mrp_picking_types:
            return

        MrpProduction = self.env['mrp.production']
        count_mo_waiting = MrpProduction.search_count([('availability', '=', 'waiting')])
        count_mo_todo = MrpProduction.search_count([('state', 'in', ('confirmed', 'planned', 'progress'))])
        count_mo_late = MrpProduction.search_count(['&', ('date_planned_start', '<', fields.Date.today()), ('state', '=', 'confirmed')])
        for picking in mrp_picking_types:
            picking.count_mo_waiting = count_mo_waiting
            picking.count_mo_todo = count_mo_todo
            picking.count_mo_late = count_mo_late
