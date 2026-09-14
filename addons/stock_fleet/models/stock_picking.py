from odoo import Command, api, fields, models
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    dispatch_management = fields.Boolean(
        help="Enable this option to display dispatch management related details in the batch/wave form view and operations kanban overview."
    )
    dock_ids = fields.Many2many(
        comodel_name="stock.location",
        relation="dock_location_stock_picking_type_rel",
        compute="_compute_dock_ids",
        store=True,
        readonly=False,
        domain="[('warehouse_id', '=', warehouse_id), ('usage', '=', 'internal')]",
    )

    @api.depends("warehouse_id")
    def _compute_dock_ids(self):
        for picking_type in self:
            if (
                picking_type.warehouse_id != picking_type._origin.warehouse_id
                and picking_type.dock_ids
            ):
                picking_type.dock_ids = [Command.clear()]


class StockPicking(models.Model):
    _inherit = "stock.picking"

    zip = fields.Char(
        related="partner_id.zip",
        string="Zip",
        search="_search_zip",
    )

    def _search_zip(self, operator, value):
        return [("partner_id.zip", operator, value)]

    def write(self, vals):
        _debug.lifecycle("fleet_picking_write", pickings=self, fields=len(vals))
        res = super().write(vals)
        if "batch_id" not in vals:
            return res
        batch = self.env["stock.picking.batch"].browse(vals.get("batch_id"))
        if batch and batch.dock_id:
            batch._set_moves_destination_to_dock()
        else:
            self._reset_location()
        return res

    def _reset_location(self):
        _debug.logic("fleet_picking_location_reset", pickings=self)
        for picking in self:
            moves = picking.move_ids.filtered(
                lambda m, dest=picking.location_dest_id: (
                    not m.location_dest_id._is_child_of(dest)
                )
            )
            moves.write({"location_dest_id": picking.location_dest_id.id})
