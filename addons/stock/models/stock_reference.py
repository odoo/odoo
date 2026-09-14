from odoo import api, fields, models

from ..tools import debug_log as dbg


class StockReference(models.Model):
    _name = "stock.reference"
    _description = "Reference between stock documents"

    name = fields.Char(
        string="Reference",
        readonly=True,
        required=True,
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

    @api.depends("move_ids.picking_id")
    def _compute_picking_ids(self):
        dbg.lifecycle.debug("_compute_picking_ids on %s", dbg.rec(self))
        for reference in self:
            reference.picking_ids = reference.move_ids.picking_id
