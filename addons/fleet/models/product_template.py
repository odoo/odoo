from datetime import datetime

from odoo import api, fields, models

FUEL_TYPES = [
    ("diesel", "Diesel"),
    ("gasoline", "Gasoline"),
    ("full_hybrid", "Full Hybrid"),
    ("plug_in_hybrid_diesel", "Plug-in Hybrid Diesel"),
    ("plug_in_hybrid_gasoline", "Plug-in Hybrid Gasoline"),
    ("cng", "CNG"),
    ("lpg", "LPG"),
    ("hydrogen", "Hydrogen"),
    ("electric", "Electric"),
]


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_vehicle = fields.Boolean(
        compute="_compute_is_vehicle",
        search="_search_is_vehicle",
    )
    vehicle_model_year = fields.Selection(
        selection="_selection_vehicle_model_years",
        string="Model Year",
    )
    vehicle_color = fields.Char(string="Color")
    seats = fields.Integer(string="Seating Capacity")
    doors = fields.Integer(
        string="Number of Doors",
        help="Specifies the total number of doors, including the trunk and hatch doors, if applicable.",
    )
    trailer_hook = fields.Boolean(
        string="Trailer Hitch",
        help="A trailer hitch is a device attached to a vehicle's chassis for towing trailers, boats or other vehicles.",
    )
    transmission = fields.Selection(
        selection=[("manual", "Manual"), ("automatic", "Automatic")]
    )
    drive_type = fields.Selection(
        selection=[
            ("fwd", "Front-Wheel Drive (FWD)"),
            ("awd", "All-Wheel Drive (AWD)"),
            ("rwd", "Rear-Wheel Drive (RWD)"),
            ("4wd", "Four-Wheel Drive (4WD)"),
        ]
    )
    fuel_type = fields.Selection(selection=FUEL_TYPES)
    power = fields.Float(help="Power of the vehicle, in the power unit.")
    power_unit = fields.Selection(
        selection=[("power", "kW"), ("horsepower", "Horsepower (hp)")],
        default="power",
    )
    horsepower = fields.Float()
    co2 = fields.Float(
        string="CO₂ Emissions",
        aggregator=None,
    )
    co2_emission_unit = fields.Selection(
        selection=[("g/km", "g/km"), ("g/mi", "g/mi")],
        compute="_compute_co2_emission_unit",
    )
    vehicle_range = fields.Integer(string="Range")
    range_unit = fields.Selection(
        selection=[("km", "km"), ("mi", "mi")],
        default="km",
    )
    fuel_tank_capacity = fields.Float(
        digits=(10, 2),
        aggregator="avg",
        help="Total fuel tank capacity in liters",
    )
    fuel_efficiency_theoretical = fields.Float(
        aggregator="avg",
        help="Manufacturer-rated fuel efficiency. Unit (km/L or MPG) is configurable in system settings.",
    )
    fuel_efficiency_min = fields.Float(
        aggregator="avg",
        help="Worst-case fuel efficiency (e.g., city driving). Unit (km/L or MPG) is configurable in system settings.",
    )
    fuel_efficiency_max = fields.Float(
        aggregator="avg",
        help="Best-case fuel efficiency (e.g., highway driving). Unit (km/L or MPG) is configurable in system settings.",
    )
    fuel_efficiency_uom_name = fields.Char(
        string="Fuel Efficiency Unit",
        compute="_compute_fuel_efficiency_uom_name",
    )

    def _compute_fuel_efficiency_uom_name(self):
        self.fuel_efficiency_uom_name = (
            self._get_fuel_efficiency_uom_name_from_ir_config_parameter()
        )

    def _selection_vehicle_model_years(self):
        return [(str(year), str(year)) for year in range(1970, datetime.now().year + 2)]

    @api.depends("asset_kind_id")
    def _compute_is_vehicle(self):
        vehicle_kind = self.env.ref(
            "resource_asset.kind_vehicle", raise_if_not_found=False
        )
        for template in self:
            template.is_vehicle = bool(vehicle_kind) and (
                template.asset_kind_id == vehicle_kind
            )

    def _search_is_vehicle(self, operator, value):
        if operator not in ("in", "not in"):
            return NotImplemented
        vehicle_kind = self.env.ref(
            "resource_asset.kind_vehicle", raise_if_not_found=False
        )
        kinds = vehicle_kind.ids if vehicle_kind else []
        wants = True in value
        if (operator == "in") == wants:
            return [("asset_kind_id", "in", kinds)]
        return [("asset_kind_id", "not in", kinds)]

    @api.depends("range_unit")
    def _compute_co2_emission_unit(self):
        for template in self:
            template.co2_emission_unit = (
                "g/mi" if template.range_unit == "mi" else "g/km"
            )
