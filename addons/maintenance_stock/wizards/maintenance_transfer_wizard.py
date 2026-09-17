from odoo import api, fields, models
from odoo.exceptions import UserError


class MaintenanceTransferWizard(models.TransientModel):
    _name = "maintenance.transfer.wizard"
    _description = "Send Equipment to Maintenance"

    order_id = fields.Many2one(
        comodel_name="maintenance.order",
        readonly=True,
        required=True,
    )
    lot_ids = fields.Many2many(related="order_id.lot_ids")
    location_id = fields.Many2one(
        comodel_name="stock.location",
        string="Source Location",
        compute="_compute_route",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )
    location_dest_id = fields.Many2one(
        comodel_name="stock.location",
        string="Destination Location",
        compute="_compute_route",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
        domain="[('maintenance_location', '=', True)]",
    )
    picking_type_id = fields.Many2one(
        comodel_name="stock.picking.type",
        string="Operation Type",
        compute="_compute_route",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )

    @api.depends("order_id")
    def _compute_route(self):
        for wizard in self:
            route = wizard.order_id and wizard.order_id._resolve_warehouse_route()
            if route:
                wizard.location_id, wizard.location_dest_id, wizard.picking_type_id = (
                    route
                )
            else:
                wizard.location_id = wizard.order_id._get_lot_location()
                wizard.location_dest_id = False
                wizard.picking_type_id = False

    def action_send(self):
        self.check_singleton()
        if not self.lot_ids:
            raise UserError(
                self.env._(
                    "%(order)s names no serialised asset to send.",
                    order=self.order_id.display_name,
                )
            )
        picking = self.order_id._create_transfer(
            self.location_id, self.location_dest_id, self.picking_type_id
        )
        return {
            "type": "ir.actions.act_window",
            "res_model": "stock.picking",
            "res_id": picking.id,
            "view_mode": "form",
            "target": "current",
        }
