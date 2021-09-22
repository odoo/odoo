# -*- coding: utf-8 -*-

from collections import defaultdict
from odoo import api, fields, models, _

class ProductionLot(models.Model):
    _inherit = 'stock.production.lot'

    repair_order_ids = fields.Many2many('repair.order', string="Repair Orders", compute="_compute_repair_order_ids")
    repair_order_count = fields.Integer('Repair order count', compute="_compute_repair_order_ids")

    @api.depends('name')
    def _compute_repair_order_ids(self):
        repair_orders = defaultdict(lambda: self.env['repair.order'])
        for repair_line in self.env['repair.line'].search([('lot_id', 'in', self.ids), ('state', '=', 'done')]):
            repair_orders[repair_line.lot_id.id] |= repair_line.repair_id
        for lot in self:
            lot.repair_order_ids = repair_orders[lot.id]
            lot.repair_order_count = len(lot.repair_order_ids)

    def action_view_ro(self):
        self.ensure_one()

        action = {
            'res_model': 'repair.order',
            'type': 'ir.actions.act_window'
        }
        if len(self.repair_order_ids) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': self.repair_order_ids[0].id
            })
        else:
            action.update({
                'name': _("Repair orders of %s", self.name),
                'domain': [('id', 'in', self.repair_order_ids.ids)],
                'view_mode': 'tree,form'
            })
        return action
