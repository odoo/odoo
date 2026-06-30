from odoo import fields, models


class StockReference(models.Model):
    _name = 'stock.reference'
    _description = 'Reference between stock documents'

    name = fields.Char('Reference', required=True, readonly=True)
    move_ids = fields.Many2many(
        'stock.move', 'stock_reference_move_rel', 'reference_id', 'move_id', string="Stock Moves")
    picking_ids = fields.Many2many('stock.picking', compute='_compute_picking_ids', string="Transfers", readonly=True)

    def _compute_picking_ids(self):
        for reference in self:
            reference.picking_ids = reference.move_ids.picking_id
