from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain


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
    range_unit = fields.Selection(related="product_id.range_unit")
    odometer = fields.Float(
        inverse="_inverse_odometer",
        readonly=False,
    )
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
