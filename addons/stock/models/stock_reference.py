from odoo import fields, models


class StockReference(models.Model):
    _name = "stock.reference"
    _description = "Reference between stock documents"

    name = fields.Char(
        string="Reference",
        required=True,
        readonly=True,
    )
    move_ids = fields.Many2many(
        comodel_name="stock.move",
        relation="stock_reference_move_rel",
        column1="reference_id",
        column2="move_id",
        string="Stock Moves",
    )
    picking_ids = fields.Many2many(
        comodel_name="stock.picking",
        string="Transfers",
        compute="_compute_picking_ids",
        readonly=True,
    )

    def _compute_picking_ids(self):
        for reference in self:
            reference.picking_ids = reference.move_ids.picking_id
