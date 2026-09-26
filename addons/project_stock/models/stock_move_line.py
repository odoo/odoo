# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    project_id = fields.Many2one('project.project', 'Project', related='move_id.project_id', store=True)
