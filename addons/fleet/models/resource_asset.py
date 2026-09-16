from collections import defaultdict
from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain

DRIVER_ROLE = "driver"
DEFAULT_HANDOVER_DELAY = timedelta(days=7)


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    is_vehicle = fields.Boolean(
        compute="_compute_is_vehicle",
        store=True,
        index=True,
    )
    driver_id = fields.Many2one(
        comodel_name="resource.resource",
        compute="_compute_driver_id",
        inverse="_inverse_driver_id",
        search="_search_driver_id",
        domain="[('resource_type', '=', 'user')]",
        help="Who drives the vehicle now: the live driver assignment.",
    )
    future_driver_id = fields.Many2one(
        comodel_name="resource.resource",
        compute="_compute_future_driver",
        inverse="_inverse_future_driver",
        search="_search_future_driver_id",
        domain="[('resource_type', '=', 'user')]",
        help="Who takes the vehicle over next: the planned driver assignment.",
    )
    next_assignation_date = fields.Datetime(
        string="Assignment Date",
        compute="_compute_future_driver",
        inverse="_inverse_future_driver",
        help="When the next driver takes the vehicle over. A hand-over without a date takes effect in a week unless accepted before.",
    )
    company_country_code = fields.Char(related="company_id.country_id.code")
    manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Fleet Manager",
        domain="[('share', '=', False)]",
        tracking=True,
    )
    tag_ids = fields.Many2many(
        comodel_name="fleet.vehicle.tag",
        relation="resource_asset_fleet_vehicle_tag_rel",
        column1="asset_id",
        column2="tag_id",
        string="Tags",
        copy=False,
    )
    model_year = fields.Char(
        compute="_compute_model_year",
        precompute=True,
        store=True,
        readonly=False,
    )
    manufacturer_id = fields.Many2one(
        related="product_id.manufacturer_id",
        string="Manufacturer",
    )
    vehicle_color = fields.Char(related="product_id.vehicle_color")
    seats = fields.Integer(related="product_id.seats")
    doors = fields.Integer(related="product_id.doors")
    trailer_hook = fields.Boolean(related="product_id.trailer_hook")
    transmission = fields.Selection(related="product_id.transmission")
    fuel_type = fields.Selection(related="product_id.fuel_type")
    power = fields.Float(related="product_id.power")
    power_unit = fields.Selection(related="product_id.power_unit")
    horsepower = fields.Float(related="product_id.horsepower")
    co2 = fields.Float(related="product_id.co2")
    co2_emission_unit = fields.Selection(related="product_id.co2_emission_unit")
    vehicle_range = fields.Integer(related="product_id.vehicle_range")
    range_unit = fields.Selection(related="product_id.range_unit")
    odometer = fields.Float(
        inverse="_inverse_odometer",
        readonly=False,
    )
    service_count = fields.Integer(compute="_compute_service_count")
    driver_history_count = fields.Integer(compute="_compute_driver_history_count")

    @api.depends("kind_id")
    def _compute_is_vehicle(self):
        vehicle_kind = self.env.ref(
            "resource_asset.kind_vehicle", raise_if_not_found=False
        )
        for asset in self:
            asset.is_vehicle = bool(vehicle_kind) and asset.kind_id == vehicle_kind

    @api.depends("product_id")
    def _compute_model_year(self):
        for asset in self:
            if not asset.model_year and asset.product_id.vehicle_model_year:
                asset.model_year = asset.product_id.vehicle_model_year

    @api.depends("product_id", "license_plate", "name", "is_vehicle")
    def _compute_display_name(self):
        vehicles = self.filtered("is_vehicle")
        for vehicle in vehicles:
            parts = [
                part
                for part in (
                    vehicle.product_id.manufacturer_id.name,
                    vehicle.product_id.name,
                )
                if part
            ] or [vehicle.name or ""]
            parts.append(vehicle.license_plate or self.env._("No Plate"))
            vehicle.display_name = " / ".join(parts)
        super(ResourceAsset, self - vehicles)._compute_display_name()

    def _get_driver_assignments(self, planned=False):
        if not self.ids:
            return self.env["resource.assignment"]
        now = fields.Datetime.now()
        domain = Domain("resource_id", "in", self.sudo().resource_id.ids) & Domain(
            "role", "=", DRIVER_ROLE
        )
        if planned:
            domain &= Domain("date_start", ">", now) & Domain("date_end", "=", False)
        else:
            domain &= Domain("date_start", "<=", now) & (
                Domain("date_end", "=", False) | Domain("date_end", ">", now)
            )
        return self.env["resource.assignment"].sudo().search(domain)

    def _first_by_asset(self, assignments, reverse):
        asset_by_resource = {asset.sudo().resource_id.id: asset for asset in self}
        first = {}
        for assignment in assignments.sorted("date_start", reverse=reverse):
            asset = asset_by_resource.get(assignment.resource_id.id)
            if asset:
                first.setdefault(asset.id, assignment)
        return first

    @api.depends(
        "resource_id.assignment_ids.assignee_id",
        "resource_id.assignment_ids.role",
        "resource_id.assignment_ids.date_start",
        "resource_id.assignment_ids.date_end",
        "resource_id.assignment_ids.active",
    )
    def _compute_driver_id(self):
        live = self._first_by_asset(self._get_driver_assignments(), reverse=True)
        for asset in self:
            assignment = live.get(asset.id)
            asset.driver_id = assignment.assignee_id if assignment else False

    @api.depends(
        "resource_id.assignment_ids.assignee_id",
        "resource_id.assignment_ids.role",
        "resource_id.assignment_ids.date_start",
        "resource_id.assignment_ids.date_end",
        "resource_id.assignment_ids.active",
    )
    def _compute_future_driver(self):
        planned = self._first_by_asset(
            self._get_driver_assignments(planned=True), reverse=False
        )
        for asset in self:
            assignment = planned.get(asset.id)
            asset.future_driver_id = assignment.assignee_id if assignment else False
            asset.next_assignation_date = assignment.date_start if assignment else False

    def _search_driver(self, operator, value, planned):
        now = fields.Datetime.now()
        if planned:
            window = Domain("date_start", ">", now) & Domain("date_end", "=", False)
        else:
            window = Domain("date_start", "<=", now) & (
                Domain("date_end", "=", False) | Domain("date_end", ">", now)
            )
        live = Domain("role", "=", DRIVER_ROLE) & window
        if operator in ("in", "not in"):
            ids = [value] if isinstance(value, (int, bool)) else list(value)
            resource_ids = [i for i in ids if i]
            wants_empty = len(resource_ids) < len(ids)
        elif operator in ("ilike", "not ilike", "=ilike", "like", "=like"):
            resource_ids = (
                self.env["resource.resource"]
                .with_context(active_test=False)
                ._search([("name", operator.removeprefix("not "), value)])
            )
            wants_empty = False
        else:
            return NotImplemented
        domain = Domain(
            "resource_id.assignment_ids",
            "any",
            live & Domain("assignee_id", "in", resource_ids),
        )
        if wants_empty:
            domain |= ~Domain("resource_id.assignment_ids", "any", live)
        return ~domain if operator.startswith("not") else domain

    def _search_driver_id(self, operator, value):
        return self._search_driver(operator, value, planned=False)

    def _search_future_driver_id(self, operator, value):
        return self._search_driver(operator, value, planned=True)

    def _inverse_driver_id(self):
        now = fields.Datetime.now()
        live = self._get_driver_assignments()
        live_by_resource = defaultdict(live.browse)
        for assignment in live:
            live_by_resource[assignment.resource_id.id] |= assignment
        new_vals_list = []
        for asset in self:
            resource = asset.sudo().resource_id
            current = live_by_resource[resource.id]
            if asset.driver_id and current.assignee_id == asset.driver_id:
                continue
            previous = current.assignee_id[:1]
            self._end_custody(current, now)
            if asset.driver_id:
                new_vals_list.append(
                    {
                        "resource_id": resource.id,
                        "assignee_id": asset.driver_id.id,
                        "role": DRIVER_ROLE,
                        "date_start": now,
                    }
                )
            asset._post_driver_message(previous, asset.driver_id)
        if new_vals_list:
            self.env["resource.assignment"].sudo().create(new_vals_list)

    def _inverse_future_driver(self):
        now = fields.Datetime.now()
        planned = self._get_driver_assignments(planned=True)
        planned_by_resource = defaultdict(planned.browse)
        for assignment in planned:
            planned_by_resource[assignment.resource_id.id] |= assignment
        new_vals_list = []
        for asset in self:
            resource = asset.sudo().resource_id
            rows = planned_by_resource[resource.id]
            date_start = asset.next_assignation_date or now + DEFAULT_HANDOVER_DELAY
            current = rows.sorted("date_start")[:1]
            if (
                asset.future_driver_id
                and current.assignee_id == asset.future_driver_id
                and current.date_start == date_start
            ):
                continue
            self._end_custody(rows, now)
            if asset.future_driver_id:
                if date_start <= now:
                    raise UserError(
                        self.env._("A scheduled hand-over must start in the future.")
                    )
                new_vals_list.append(
                    {
                        "resource_id": resource.id,
                        "assignee_id": asset.future_driver_id.id,
                        "role": DRIVER_ROLE,
                        "date_start": date_start,
                    }
                )
        if new_vals_list:
            self.env["resource.assignment"].sudo().create(new_vals_list)

    def _post_driver_message(self, before, after):
        self.check_singleton()
        if before == after:
            return
        self.sudo().message_post(
            body=self.env._(
                "Driver: %(before)s → %(after)s",
                before=before.sudo().name or "—",
                after=after.sudo().name or "—",
            ),
            subtype_xmlid="fleet.mt_fleet_driver_updated",
        )

    def _get_vehicles_released_by_driver_change(self):
        return self.search(
            [
                ("is_vehicle", "=", True),
                ("driver_id", "in", self.future_driver_id.ids),
                ("id", "not in", self.ids),
            ]
        )

    def action_accept_driver_change(self):
        vehicles = self.filtered("future_driver_id")
        vehicles._get_vehicles_released_by_driver_change().driver_id = False
        now = fields.Datetime.now()
        for vehicle in vehicles:
            planned = vehicle._get_driver_assignments(planned=True).sorted(
                "date_start"
            )[:1]
            previous = vehicle.driver_id
            self._end_custody(vehicle._get_driver_assignments(), now)
            planned.date_start = now
            vehicle.invalidate_recordset(
                ["driver_id", "future_driver_id", "next_assignation_date"]
            )
            vehicle._post_driver_message(previous, vehicle.driver_id)

    def _inverse_odometer(self):
        for asset in self:
            meter = asset.odometer_meter_id
            if not asset.odometer and not meter:
                continue
            if not meter:
                meter = self.env["resource.asset.meter"].create(
                    {
                        "asset_id": asset.id,
                        "name": self.env._("Odometer"),
                        "kind": "odometer",
                        "uom_id": asset.odometer_uom_id.id,
                    }
                )
            if meter.value > asset.odometer:
                raise ValidationError(
                    self.env._(
                        "%(vehicle)s: the odometer cannot go below its last reading of %(value)s.",
                        vehicle=asset.display_name,
                        value=meter.value,
                    )
                )
            if meter.value != asset.odometer:
                meter.record(asset.odometer)

    def _get_service_domain(self):
        return Domain("asset_id", "in", self.ids) & Domain("log_type", "=", "service")

    def _compute_service_count(self):
        counts = dict(
            self.env["resource.asset.log"]._read_group(
                self._get_service_domain(), ["asset_id"], ["__count"]
            )
        )
        for asset in self:
            asset.service_count = counts.get(asset, 0)

    def _compute_driver_history_count(self):
        counts = dict(
            self.env["resource.assignment"]._read_group(
                [
                    ("resource_id", "in", self.resource_id.ids),
                    ("role", "=", DRIVER_ROLE),
                ],
                ["resource_id"],
                ["__count"],
            )
        )
        for asset in self:
            asset.driver_history_count = counts.get(asset.resource_id, 0)

    def action_view_services(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "fleet.fleet_vehicle_service_action"
        )
        action["domain"] = [("asset_id", "=", self.id), ("log_type", "=", "service")]
        action["context"] = {
            "default_asset_id": self.id,
            "search_default_groupby_product": 1,
        }
        return action

    def action_view_driver_history(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Drivers"),
            "view_mode": "list,form",
            "res_model": "resource.assignment",
            "domain": [
                ("resource_id", "=", self.resource_id.id),
                ("role", "=", DRIVER_ROLE),
            ],
            "context": {
                "default_resource_id": self.resource_id.id,
                "default_role": DRIVER_ROLE,
                "active_test": False,
            },
        }

    def action_view_odometer(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "fleet.fleet_vehicle_odometer_action"
        )
        action["domain"] = [
            ("asset_id", "=", self.id),
            ("meter_id.kind", "=", "odometer"),
        ]
        return action

    def action_send_email(self):
        return {
            "name": self.env._("Send Email"),
            "type": "ir.actions.act_window",
            "target": "new",
            "view_mode": "form",
            "res_model": "fleet.vehicle.send.mail",
            "context": {"default_vehicle_ids": self.ids},
        }
