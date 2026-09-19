from odoo import api, fields, models

from odoo.addons.resource_asset.fields import AssetIdentifier


class ResourceAssetVehicle(models.Model):
    """A vehicle is an asset whose rows live in their own table.

    Everything a vehicle is remains declared on `resource.asset`, so a
    reference held as `resource.asset` still reads and writes it: PostgreSQL's
    SELECT, UPDATE and DELETE on a parent reach the children unless told ONLY.
    What this model buys is a place to put what only vehicles have -- access
    rights, record rules, views, actions and, later, columns no other kind
    carries.
    """

    _name = "resource.asset.vehicle"
    _description = "Vehicle"
    _inherit = ["resource.asset"]
    _table = "resource_asset_vehicle"

    # The root reads these through the identifier rows; the vehicle holds them.
    license_plate = AssetIdentifier(
        identifier_code="plate",
        store=True,
    )
    vin_sn = AssetIdentifier(
        identifier_code="vin",
        store=True,
    )
    engine_sn = AssetIdentifier(
        identifier_code="engine",
        store=True,
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

    @api.depends("product_id")
    def _compute_model_year(self):
        for asset in self:
            if not asset.model_year and asset.product_id.vehicle_model_year:
                asset.model_year = asset.product_id.vehicle_model_year

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
