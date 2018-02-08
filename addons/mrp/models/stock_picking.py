# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    code = fields.Selection(selection_add=[('mrp_operation', 'Manufacturing Operation')])
    count_mo_todo = fields.Integer(string="Number of Manufacturing Orders to Process",
        compute='_get_mo_count')
    count_mo_waiting = fields.Integer(string="Number of Manufacturing Orders Waiting",
        compute='_get_mo_count')
    count_mo_late = fields.Integer(string="Number of Manufacturing Orders Late",
        compute='_get_mo_count')

    def _get_mo_count(self):
        mrp_picking_types = self.filtered(lambda picking: picking.code == 'mrp_operation')
        if not mrp_picking_types:
            return
        domains = {
            'count_mo_waiting': [('availability', '=', 'waiting')],
            'count_mo_todo': [('state', 'in', ('confirmed', 'planned', 'progress'))],
            'count_mo_late': [('date_planned_start', '<', fields.Date.today()), ('state', '=', 'confirmed')],
        }
        for field in domains:
            data = self.env['mrp.production'].read_group(domains[field] +
                [('state', 'not in', ('done', 'cancel')), ('picking_type_id', 'in', self.ids)],
                ['picking_type_id'], ['picking_type_id'])
            count = {x['picking_type_id'] and x['picking_type_id'][0]: x['picking_type_id_count'] for x in data}
            for record in mrp_picking_types:
                record[field] = count.get(record.id, 0)

    def get_mrp_stock_picking_action_picking_type(self):
        return self._get_action('mrp.mrp_production_action_picking_deshboard')
