# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import api, fields, models, _


class StockLot(models.Model):
    _inherit = 'stock.lot'

    repair_line_ids = fields.Many2many('repair.order', string="Repair Orders", compute="_compute_repair_line_ids")
    repair_part_count = fields.Integer('Repair part count', compute="_compute_repair_line_ids")
    in_repair_count = fields.Integer('In repair count', compute="_compute_in_repair_count")
    repaired_count = fields.Integer('Repaired count', compute='_compute_repaired_count')

    @api.depends('name')
    def _compute_repair_line_ids(self):
        repair_orders = defaultdict(lambda: self.env['repair.order'])
        repair_moves = self.env['stock.move'].search([
            ('repair_id', '!=', False),
            ('repair_line_type', '!=', False),
            ('move_line_ids.lot_id', 'in', self.ids),
            ('state', '=', 'done')])
        for repair_line in repair_moves:
            for rl_id in repair_line.lot_ids.ids:
                repair_orders[rl_id] |= repair_line.repair_id
        for lot in self:
            lot.repair_line_ids = repair_orders[lot.id]
            lot.repair_part_count = len(lot.repair_line_ids)

    def _compute_in_repair_count(self):
        lot_data = self.env['repair.order']._read_group([('lot_id', 'in', self.ids), ('state', 'not in', ('done', 'cancel'))], ['lot_id'], ['__count'])
        result = {lot.id: count for lot, count in lot_data}
        for lot in self:
            lot.in_repair_count = result.get(lot.id, 0)

    def _compute_repaired_count(self):
        lot_data = self.env['repair.order']._read_group([('lot_id', 'in', self.ids), ('state', '=', 'done')], ['lot_id'], ['__count'])
        result = {lot.id: count for lot, count in lot_data}
        for lot in self:
            lot.repaired_count = result.get(lot.id, 0)

    def action_lot_open_repairs(self):
        action = self.env["ir.actions.actions"]._for_xml_id("repair.action_repair_order_tree")
        action.update({
            'domain': [('lot_id', '=', self.id)],
            'context': {
                'default_product_id': self.product_id.id,
                'default_repair_lot_id': self.id,
                'default_company_id': self.company_id.id,
            },
        })
        return action

    def action_view_ro(self):
        self.ensure_one()

        action = {
            'res_model': 'repair.order',
            'type': 'ir.actions.act_window'
        }
        if len(self.repair_line_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.repair_line_ids[0].id
            })
        else:
            action.update({
                'name': _("Repair orders of %s", self.name),
                'domain': [('id', 'in', self.repair_line_ids.ids)],
                'view_mode': 'tree,form'
            })
        return action
