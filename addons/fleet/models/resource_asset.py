from odoo import api, fields, models


class ResourceAsset(models.Model):
    _inherit = "resource.asset"

    is_vehicle = fields.Boolean(
        compute="_compute_is_vehicle",
        store=True,
        index=True,
    )
    company_country_code = fields.Char(related="company_id.country_id.code")
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
    fuel_tank_capacity = fields.Float(
        related="product_id.fuel_tank_capacity",
        digits=(10, 2),
    )
    range_unit = fields.Selection(related="product_id.range_unit")
    service_count = fields.Integer(compute="_compute_service_count")

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

    @api.depends("product_id", "license_plate", "vin_sn", "name", "is_vehicle")
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
            ]
            parts.append(vehicle._get_display_identity())
            vehicle.display_name = " / ".join(parts)
        super(ResourceAsset, self - vehicles)._compute_display_name()

    def _get_display_identity(self):
        """What names this unit among others of its model. A plate is how a
        vehicle is spoken about, but one waiting for its paperwork has none --
        and a serial says more about which vehicle this is than "No Plate"
        does."""
        self.check_singleton()
        if self.license_plate or self.vin_sn:
            return self.license_plate or self.vin_sn
        # The asset's own name is composed from its model and its serial, and
        # the model is already the part before this one -- the same reason the
        # plate is not appended to a label that ends in it.
        name = self.name or ""
        model = self.product_id.name or ""
        if model and name.startswith(f"{model} "):
            name = name[len(model) + 1 :]
        return name or self.env._("No Plate")

    def _compute_service_count(self):
        counts = self._get_log_counts_by_type()
        for asset in self:
            asset.service_count = counts[asset.id]["service"]

    def action_view_services(self):
        return self._action_view_logs(
            [("log_type", "=", "service")],
            {"search_default_groupby_product": 1},
            xml_id="fleet.fleet_vehicle_service_action",
        )

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
