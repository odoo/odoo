from odoo import Command, api, fields, models
from odoo.exceptions import UserError
from odoo.libs.debug_log import DebugLog

_debug = DebugLog(__name__)


class MaintenanceOrder(models.Model):
    _inherit = "maintenance.order"

    # FIELDS
    lot_ids = fields.Many2many(
        comodel_name="stock.lot",
        string="Serial Numbers",
        compute="_compute_lot_ids",
        search="_search_lot_ids",
    )
    picking_ids = fields.One2many(
        comodel_name="stock.picking",
        inverse_name="maintenance_order_id",
        string="Transfers",
    )
    picking_count = fields.Count(count_of="picking_ids")
    is_sent = fields.Boolean(
        compute="_compute_is_sent",
        help="The equipment has a transfer to maintenance that is not cancelled.",
    )
    date_returned = fields.Datetime(
        string="Returned On",
        compute="_compute_return_dates",
        store=True,
    )
    return_delay_days = fields.Float(
        compute="_compute_return_dates",
        store=True,
        help="Days between the planned end and the return from maintenance; negative is early.",
    )
    is_returned_on_time = fields.Boolean(
        string="Returned On Time",
        compute="_compute_return_dates",
        store=True,
    )
    asset_log_ids = fields.One2many(
        comodel_name="resource.asset.log",
        inverse_name="maintenance_order_id",
        string="Service Logs",
        readonly=True,
    )

    # COMPUTE METHODS
    @api.depends("asset_ids.lot_id")
    def _compute_lot_ids(self):
        for order in self:
            order.lot_ids = order.asset_ids.lot_id

    @api.depends("picking_ids.return_id", "picking_ids.state")
    def _compute_is_sent(self):
        for order in self:
            order.is_sent = bool(order._get_outgoing_transfer())

    @api.depends(
        "picking_ids.return_id",
        "picking_ids.state",
        "picking_ids.date_done",
        "picking_ids.move_line_ids.lot_id",
        "resource_ids",
        "date_scheduled_end",
    )
    def _compute_return_dates(self):
        for order in self:
            returns = order.picking_ids.filtered(
                lambda picking: (
                    picking._is_maintenance_return() and picking.state == "done"
                )
            )
            back = returns.move_line_ids.lot_id
            returned = order.lot_ids <= back and max(
                returns.mapped("date_done"), default=False
            )
            order.date_returned = returned
            if returned and order.date_scheduled_end:
                delay = (returned - order.date_scheduled_end).total_seconds()
                order.return_delay_days = delay / 86400
                order.is_returned_on_time = delay <= 0
            else:
                order.return_delay_days = 0.0
                order.is_returned_on_time = False

    # SEARCH METHODS
    def _search_lot_ids(self, operator, value):
        if operator in ("in", "not in"):
            lot_domain = [("lot_id", "in", value)]
        elif operator in ("any", "not any"):
            lot_domain = [("lot_id", "any", value)]
        else:
            return NotImplemented
        return [
            (
                "asset_ids",
                "not any" if operator.startswith("not") else "any",
                lot_domain,
            )
        ]

    # ACTION METHODS
    def action_send_to_maintenance(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Send to Maintenance"),
            "res_model": "maintenance.transfer.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_order_id": self.id},
        }

    def action_view_transfers(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "stock.action_picking_tree_all"
        )
        action["domain"] = [("maintenance_order_id", "=", self.id)]
        action["context"] = {"create": False}
        return action

    # TRANSFER METHODS
    def _create_transfer(self, location, location_dest, picking_type):
        self.check_singleton()
        if self.state not in ("confirmed", "in_progress"):
            raise UserError(
                self.env._(
                    "%(order)s must be confirmed before it is sent to maintenance.",
                    order=self.display_name,
                )
            )
        if self._get_outgoing_transfer():
            raise UserError(
                self.env._(
                    "%(order)s is already on its way to maintenance.",
                    order=self.display_name,
                )
            )
        _debug.lifecycle(
            "maintenance_transfer_created",
            order=self,
            source=location,
            destination=location_dest,
            picking_type=picking_type,
            lots=self.lot_ids,
        )
        picking = self.env["stock.picking"].create(
            self._prepare_transfer_vals(location, location_dest, picking_type)
        )
        picking.action_confirm()
        lots = self.lot_ids.grouped("product_id")
        for move in picking.move_ids:
            move.lot_ids = lots[move.product_id]
        return picking

    def _mark_sent(self):
        _debug.lifecycle("maintenance_equipment_sent", orders=self)
        self.filtered(lambda order: order.state == "confirmed").action_start()

    def _mark_returned(self, return_picking):
        Log = self.env["resource.asset.log"]
        _debug.lifecycle(
            "maintenance_equipment_returned",
            orders=self,
            picking=return_picking,
            lots=return_picking.move_line_ids.lot_id,
        )
        for order in self:
            for lot in return_picking.move_line_ids.lot_id & order.lot_ids:
                if Log.search_count(  # noqa: E8507 - one probe per returned serial, which arrives one transfer at a time
                    [
                        ("maintenance_order_id", "=", order.id),
                        ("asset_id", "=", lot.asset_id.id),
                        ("log_type", "=", "service"),
                    ],
                    limit=1,
                ):
                    continue
                Log.create(order._prepare_service_log_vals(lot, return_picking))
            if order.state in ("confirmed", "in_progress") and order.date_returned:
                order.write(
                    {
                        "state": "done",
                        "date_done": order._get_local_date(order.date_returned),
                    }
                )

    # HELPER METHODS
    def _get_outgoing_transfer(self):
        self.check_singleton()
        return self.picking_ids.filtered(
            lambda picking: not picking.return_id and picking.state != "cancel"
        )[:1]

    def _prepare_transfer_vals(self, location, location_dest, picking_type):
        self.check_singleton()
        return {
            "picking_type_id": picking_type.id,
            "location_id": location.id,
            "location_dest_id": location_dest.id,
            "maintenance_order_id": self.id,
            "partner_id": self.vendor_id.id,
            "user_id": self.user_id.id,
            "company_id": self.company_id.id,
            "date_planned": self.date_scheduled_start or fields.Datetime.now(),
            "origin": self.name,
            "move_ids": [
                Command.create(
                    {
                        "description_picking": product.name,
                        "product_id": product.id,
                        "product_uom_qty": float(len(lots)),
                        "product_uom_id": product.uom_id.id,
                        "location_id": location.id,
                        "location_dest_id": location_dest.id,
                    }
                )
                for product, lots in self.lot_ids.grouped("product_id").items()
            ],
        }

    def _prepare_service_log_vals(self, lot, return_picking):
        self.check_singleton()
        notes = [f"Subject: {self.name}"]
        type_label = dict(self._fields["maintenance_type"].selection).get(
            self.maintenance_type
        )
        if type_label:
            notes.append(f"Type: {type_label}")
        if self.plan_id:
            notes.append(f"Plan: {self.plan_id.name}")
        if self.duration:
            notes.append(f"Duration: {self.duration} hours")
        if self.vendor_id:
            notes.append(f"Vendor: {self.vendor_id.name}")
        if self.date_scheduled_end:
            notes.append(f"Expected Return: {self.date_scheduled_end:%Y-%m-%d %H:%M}")
        returned = return_picking.date_done
        if returned:
            notes.append(f"Actual Return: {returned:%Y-%m-%d %H:%M}")
            if self.date_scheduled_end:
                delay = (returned - self.date_scheduled_end).total_seconds() / 86400
                if delay > 0:
                    notes.append(f"Delay: {delay:.1f} days late")
                elif delay < 0:
                    notes.append(f"Delivered Early: {abs(delay):.1f} days early")
        if self.description:
            notes.append(f"\nDescription:\n{self.description}")
        return {
            "asset_id": lot.asset_id.id,
            "log_type": "service",
            "source": "maintenance",
            "date": returned.date() if returned else fields.Date.today(),
            "state": "done",
            "notes": "\n".join(notes),
            "vendor_id": self.vendor_id.id,
            "maintenance_order_id": self.id,
        }

    def _get_lot_location(self):
        self.check_singleton()
        locations = self.lot_ids.location_id
        if len(locations) <= 1:
            return locations
        paths = [location.parent_path.split("/")[:-1] for location in locations]
        common = []
        for ids in zip(*paths, strict=False):
            if len(set(ids)) > 1:
                break
            common.append(ids[0])
        return self.env["stock.location"].browse(int(common[-1]) if common else [])

    def _resolve_warehouse_route(self):
        self.check_singleton()
        location = self._get_lot_location()
        warehouse = location.warehouse_id
        if not (
            warehouse.allow_maintenance
            and warehouse.wh_maintenance_stock_loc_id
            and warehouse.maintenance_type_id
        ):
            _debug.logic(
                "maintenance_route_unavailable",
                order=self,
                location=location,
                warehouse=warehouse,
            )
            return None
        return (
            location,
            warehouse.wh_maintenance_stock_loc_id,
            warehouse.maintenance_type_id,
        )

    def _get_local_date(self, moment):
        self.check_singleton()
        if self.plan_id:
            return self.plan_id._get_local_date(moment)
        return fields.Date.context_today(self, timestamp=moment)
