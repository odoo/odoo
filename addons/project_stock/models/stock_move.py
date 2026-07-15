# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockMove(models.Model):
    _inherit = 'stock.move'

    project_id = fields.Many2one('project.project', 'Project', compute='_compute_project_id', store=True)

    @api.depends('picking_id.project_id')
    def _compute_project_id(self):
        self.project_id = False
        for move in self:
            if move.picking_id:
                move.project_id = move.picking_id.project_id
