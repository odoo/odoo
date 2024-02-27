# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class StockBatchDock(models.Model):
    _name = 'stock.batch.dock'
    _description = 'Stock Batch Dock'

    name = fields.Char('Dock')
    operation_type_ids = fields.Many2many(
        'stock.picking.type', string='Operation Types',
        relation='stock_batch_dock_picking_type_rel',
        column1='dock_id', column2='picking_type_id')
    color = fields.Integer('Color Index')
