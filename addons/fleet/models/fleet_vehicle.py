from collections import defaultdict
from datetime import datetime

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.fleet.models.fleet_vehicle_model import FUEL_TYPES

# Some fields don't have the exact same name
MODEL_FIELDS_TO_VEHICLE = {
    "transmission": "transmission",
    "model_year": "model_year",
    "electric_assistance": "electric_assistance",
    "color": "color",
    "seats": "seats",
    "doors": "doors",
    "trailer_hook": "trailer_hook",
    "default_co2": "co2",
    "co2_standard": "co2_standard",
    "default_fuel_type": "fuel_type",
    "power": "power",
    "horsepower": "horsepower",
    "horsepower_tax": "horsepower_tax",
    "category_id": "category_id",
    "vehicle_range": "vehicle_range",
    "power_unit": "power_unit",
    "range_unit": "range_unit",
}


class FleetVehicle(models.Model):
    _name = "fleet.vehicle"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity", "mixin.avatar"]
    _description = "Vehicle"
    _order = "license_plate asc, acquisition_date asc"
    _rec_names_search = ["name", "driver_id.name"]

    def _default_state_id(self):
        state = self.env.ref(
            "fleet.fleet_vehicle_state_new_request", raise_if_not_found=False
        )
        return state if state and state.id else False

    def _selection_years(self):
        current_year = datetime.now().year
        return [(str(i), i) for i in range(1970, current_year + 1)]

    name = fields.Char(
        compute="_compute_name",
        store=True,
    )
    description = fields.Html(string="Vehicle Description")
    active = fields.Boolean(
        default=True,
        tracking=True,
    )
    manager_id = fields.Many2one(
        comodel_name="res.users",
        string="Fleet Manager",
        domain=lambda self: (
            f"[('share', '=', False), ('company_id', '=', company_id), ('all_group_ids', 'in', {self.env.ref('fleet.fleet_group_user').id})]"
        ),
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    country_id = fields.Many2one(
        comodel_name="res.country",
        related="company_id.country_id",
    )
    country_code = fields.Char(
        related="country_id.code",
        depends=["country_id"],
    )
    license_plate = fields.Char(
        help="License plate number of the vehicle (i = plate number for a car)",
        tracking=True,
    )
    vin_sn = fields.Char(
        string="Chassis Number",
        help="Unique number written on the vehicle motor (VIN/SN number)",
        copy=False,
        tracking=True,
    )
    trailer_hook = fields.Boolean(
        string="Trailer Hitch",
        help="A trailer hitch is a device attached to a vehicle's chassis for towing purposes, \
            such as pulling trailers, boats, or other vehicles.",
        compute="_compute_trailer_hook",
        store=True,
        readonly=False,
    )
    driver_id = fields.Many2one(
        comodel_name="res.partner",
        help="Driver address of the vehicle",
        copy=False,
        tracking=True,
    )
    future_driver_id = fields.Many2one(
        comodel_name="res.partner",
        help="Next Driver Address of the vehicle",
        copy=False,
        check_company=True,
        tracking=True,
    )
    model_id = fields.Many2one(
        comodel_name="fleet.vehicle.model",
        required=True,
        tracking=True,
    )
    brand_id = fields.Many2one(
        comodel_name="fleet.vehicle.model.brand",
        related="model_id.brand_id",
        string="Brand",
        store=True,
        readonly=False,
    )
    log_drivers = fields.One2many(
        comodel_name="fleet.vehicle.assignation.log",
        inverse_name="vehicle_id",
        string="Assignment Logs",
    )
    log_services = fields.One2many(
        comodel_name="fleet.vehicle.log.services",
        inverse_name="vehicle_id",
        string="Services Logs",
    )
    log_contracts = fields.One2many(
        comodel_name="fleet.vehicle.log.contract",
        inverse_name="vehicle_id",
        string="Contracts",
    )
    contract_count = fields.Integer(compute="_compute_count_all")
    service_count = fields.Integer(
        string="Services",
        compute="_compute_count_all",
    )
    odometer_count = fields.Integer(
        string="Odometer",
        compute="_compute_count_all",
    )
    history_count = fields.Integer(
        string="Drivers History Count",
        compute="_compute_count_all",
    )
    next_assignation_date = fields.Date(
        string="Assignment Date",
        help="This is the date at which the car will be available, if not set it means available instantly",
    )
    order_date = fields.Date()
    acquisition_date = fields.Date(
        string="Registration Date",
        help="Date of vehicle registration",
        default=fields.Date.today,
        required=False,
        tracking=True,
    )
    write_off_date = fields.Date(
        string="Cancellation Date",
        help="Date when the vehicle's license plate has been cancelled/removed.",
        tracking=True,
    )
    contract_date_start = fields.Date(
        string="First Contract Date",
        default=fields.Date.today,
        tracking=True,
    )
    color = fields.Char(
        help="Color of the vehicle",
        compute="_compute_color",
        store=True,
        readonly=False,
    )
    state_id = fields.Many2one(
        comodel_name="fleet.vehicle.state",
        help="Current state of the vehicle",
        default=_default_state_id,
        group_expand="_read_group_expand_full",
        ondelete="set null",
        tracking=True,
    )
    location = fields.Char(help="Location of the vehicle (garage, ...)")
    seats = fields.Integer(
        string="Seating Capacity",
        help="Number of seats of the vehicle",
        compute="_compute_seats",
        store=True,
        readonly=False,
    )
    model_year = fields.Selection(
        selection="_selection_years",
        help="Year of the model",
        compute="_compute_model_year",
        store=True,
        readonly=False,
    )
    doors = fields.Integer(
        string="Number of Doors",
        help="Number of doors of the vehicle",
        compute="_compute_doors",
        store=True,
        readonly=False,
    )
    tag_ids = fields.Many2many(
        comodel_name="fleet.vehicle.tag",
        relation="fleet_vehicle_vehicle_tag_rel",
        column1="vehicle_tag_id",
        column2="tag_id",
        string="Tags",
        copy=False,
    )
    odometer = fields.Float(
        string="Last Odometer",
        help="Odometer measure of the vehicle at the moment of this log",
        compute="_compute_odometer",
        inverse="_inverse_odometer",
    )
    odometer_unit = fields.Selection(
        selection=[("kilometers", "km"), ("miles", "mi")],
        default="kilometers",
        required=True,
    )
    transmission = fields.Selection(
        selection=[("manual", "Manual"), ("automatic", "Automatic")],
        compute="_compute_transmission",
        store=True,
        readonly=False,
    )
    fuel_type = fields.Selection(
        selection=FUEL_TYPES,
        compute="_compute_fuel_type",
        store=True,
        readonly=False,
    )
    power_unit = fields.Selection(
        selection=[("power", "kW"), ("horsepower", "Horsepower")],
        default="power",
        required=True,
    )
    horsepower = fields.Float(
        compute="_compute_horsepower",
        store=True,
        readonly=False,
    )
    horsepower_tax = fields.Float(
        string="Horsepower Taxation",
        compute="_compute_horsepower_tax",
        store=True,
        readonly=False,
    )
    power = fields.Float(
        help="Power in kW of the vehicle",
        compute="_compute_power",
        store=True,
        readonly=False,
    )
    co2 = fields.Float(
        string="CO₂ Emissions",
        help="CO2 emissions of the vehicle",
        compute="_compute_co2",
        store=True,
        readonly=False,
        aggregator=None,
        tracking=True,
    )
    co2_emission_unit = fields.Selection(
        selection=[("g/km", "g/km"), ("g/mi", "g/mi")],
        compute="_compute_co2_emission_unit",
        default="g/km",
        store=True,
        required=True,
    )
    co2_standard = fields.Char(
        string="Emission Standard",
        help="Emission Standard specifies the regulatory test procedure \
            or guideline under which a vehicle's emissions are measured.",
        compute="_compute_co2_standard",
        store=True,
        readonly=False,
    )
    category_id = fields.Many2one(
        comodel_name="fleet.vehicle.model.category",
        compute="_compute_category_id",
        store=True,
        readonly=False,
    )
    image_128 = fields.Image(
        related="model_id.image_128",
        readonly=True,
    )
    contract_renewal_due_soon = fields.Boolean(
        string="Has Contracts to renew",
        compute="_compute_contract_reminder",
        search="_search_contract_renewal_due_soon",
    )
    contract_renewal_overdue = fields.Boolean(
        string="Has Contracts Overdue",
        compute="_compute_contract_reminder",
        search="_search_contract_renewal_overdue",
    )
    contract_state = fields.Selection(
        selection=[
            ("futur", "Incoming"),
            ("open", "In Progress"),
            ("expired", "Expired"),
            ("closed", "Closed"),
        ],
        string="Last Contract State",
        compute="_compute_contract_reminder",
        required=False,
    )
    car_value = fields.Float(
        string="Catalog Value (VAT Incl.)",
        tracking=True,
    )
    net_car_value = fields.Float(string="Purchase Value")
    residual_value = fields.Float()
    plan_to_change_car = fields.Boolean(tracking=True)
    plan_to_change_bike = fields.Boolean(tracking=True)
    vehicle_type = fields.Selection(related="model_id.vehicle_type")
    frame_type = fields.Selection(
        selection=[("diamant", "Diamant"), ("trapez", "Trapez"), ("wave", "Wave")],
        string="Bike Frame Type",
    )
    electric_assistance = fields.Boolean(
        compute="_compute_electric_assistance",
        store=True,
        readonly=False,
    )
    frame_size = fields.Float()
    service_activity = fields.Selection(
        selection=[
            ("none", "None"),
            ("overdue", "Overdue"),
            ("today", "Today"),
        ],
        compute="_compute_service_activity",
    )
    vehicle_properties = fields.Properties(
        definition="model_id.vehicle_properties_definition",
        string="Properties",
        copy=True,
    )
    vehicle_range = fields.Integer(string="Range")
    range_unit = fields.Selection(
        selection=[("km", "km"), ("mi", "mi")],
        compute="_compute_range_unit",
        precompute=True,
        store=True,
        readonly=False,
        required=True,
    )

    @api.depends("log_services")
    def _compute_service_activity(self):
        for vehicle in self:
            vehicle.service_activity = self._most_urgent_activity_state(
                vehicle.log_services.mapped("activity_state"),
                among=("overdue", "today"),
                fallback="none",
            )

    def _load_fields_from_model(self, fields_to_load):
        """
        Copies the desired fields from the models to the vehicles
        """
        model_values = {}
        for vehicle in self.filtered("model_id"):
            if vehicle.model_id.id in model_values:
                write_vals = model_values[vehicle.model_id.id]
            else:
                # Update only the desired fields from the model, only when the model has a truthy value.
                write_vals = {
                    vehicle_field: vehicle.model_id[model_field]
                    for model_field, vehicle_field in MODEL_FIELDS_TO_VEHICLE.items()
                    if vehicle_field in fields_to_load and vehicle.model_id[model_field]
                }
                model_values[vehicle.model_id.id] = write_vals
            vehicle.update(write_vals)

    @api.depends("model_id")
    def _compute_category_id(self):
        self._load_fields_from_model(["category_id"])

    @api.depends("model_id")
    def _compute_range_unit(self):
        self._load_fields_from_model(["range_unit"])
        for vehicle in self:
            vehicle.range_unit = vehicle.range_unit or "km"

    @api.depends("model_id")
    def _compute_trailer_hook(self):
        self._load_fields_from_model(["trailer_hook"])

    @api.depends("model_id")
    def _compute_vehicle_range(self):
        self._load_fields_from_model(["vehicle_range"])

    @api.depends("model_id")
    def _compute_electric_assistance(self):
        self._load_fields_from_model(["electric_assistance"])

    @api.depends("model_id")
    def _compute_co2_standard(self):
        self._load_fields_from_model(["co2_standard"])

    @api.depends("model_id")
    def _compute_co2(self):
        self._load_fields_from_model(["co2"])

    @api.depends("model_id")
    def _compute_power(self):
        self._load_fields_from_model(["power"])

    @api.depends("model_id")
    def _compute_horsepower(self):
        self._load_fields_from_model(["horsepower"])

    @api.depends("model_id")
    def _compute_horsepower_tax(self):
        self._load_fields_from_model(["horsepower_tax"])

    @api.depends("model_id")
    def _compute_fuel_type(self):
        self._load_fields_from_model(["fuel_type"])

    @api.depends("model_id")
    def _compute_transmission(self):
        self._load_fields_from_model(["transmission"])

    @api.depends("model_id")
    def _compute_doors(self):
        self._load_fields_from_model(["doors"])

    @api.depends("model_id")
    def _compute_model_year(self):
        self._load_fields_from_model(["model_year"])

    @api.depends("model_id")
    def _compute_seats(self):
        self._load_fields_from_model(["seats"])

    @api.depends("model_id")
    def _compute_color(self):
        self._load_fields_from_model(["color"])

    @api.depends("model_id.brand_id.name", "model_id.name", "license_plate")
    def _compute_name(self):
        for record in self:
            record.name = (
                (record.model_id.brand_id.name or "")
                + "/"
                + (record.model_id.name or "")
                + "/"
                + (record.license_plate or _("No Plate"))
            )

    @api.depends("range_unit")
    def _compute_co2_emission_unit(self):
        for record in self:
            if record.range_unit == "km":
                record.co2_emission_unit = "g/km"
            else:
                record.co2_emission_unit = "g/mi"

    def _compute_odometer(self):
        odometers = self.env["fleet.vehicle.odometer"].search(
            [("vehicle_id", "in", self.ids)], order="date desc, id desc"
        )
        latest_by_vehicle = {}
        for odometer in odometers:
            latest_by_vehicle.setdefault(odometer.vehicle_id.id, odometer.value)
        for record in self:
            record.odometer = latest_by_vehicle.get(record.id, 0)

    def _inverse_odometer(self):
        self.env["fleet.vehicle.odometer"].create(
            [
                {
                    "value": vehicle.odometer,
                    "date": fields.Date.context_today(vehicle),
                    "vehicle_id": vehicle.id,
                    "driver_id": vehicle.driver_id.id,
                }
                for vehicle in self
                if vehicle.odometer
            ]
        )

    def _compute_count_all(self):
        Odometer = self.env["fleet.vehicle.odometer"]
        LogService = self.env["fleet.vehicle.log.services"].with_context(
            active_test=False
        )
        LogContract = self.env["fleet.vehicle.log.contract"].with_context(
            active_test=False
        )
        History = self.env["fleet.vehicle.assignation.log"]
        odometers_data = Odometer._read_group(
            [("vehicle_id", "in", self.ids)], ["vehicle_id"], ["__count"]
        )
        services_data = LogService._read_group(
            [("vehicle_id", "in", self.ids)], ["vehicle_id", "active"], ["__count"]
        )
        logs_data = LogContract._read_group(
            [("vehicle_id", "in", self.ids), ("state", "!=", "closed")],
            ["vehicle_id", "active"],
            ["__count"],
        )
        histories_data = History._read_group(
            [("vehicle_id", "in", self.ids)], ["vehicle_id"], ["__count"]
        )

        mapped_odometer_data = defaultdict(lambda: 0)
        mapped_service_data = defaultdict(lambda: defaultdict(lambda: 0))
        mapped_log_data = defaultdict(lambda: defaultdict(lambda: 0))
        mapped_history_data = defaultdict(lambda: 0)

        for vehicle, count in odometers_data:
            mapped_odometer_data[vehicle.id] = count
        for vehicle, active, count in services_data:
            mapped_service_data[vehicle.id][active] = count
        for vehicle, active, count in logs_data:
            mapped_log_data[vehicle.id][active] = count
        for vehicle, count in histories_data:
            mapped_history_data[vehicle.id] = count

        for vehicle in self:
            vehicle.odometer_count = mapped_odometer_data[vehicle.id]
            vehicle.service_count = mapped_service_data[vehicle.id][vehicle.active]
            vehicle.contract_count = mapped_log_data[vehicle.id][vehicle.active]
            vehicle.history_count = mapped_history_data[vehicle.id]

    @api.depends("log_contracts")
    def _compute_contract_reminder(self):
        params = self.env["ir.config_parameter"].sudo()
        delay_alert_contract = int(
            params.get_param("hr_fleet.delay_alert_contract", default=30)
        )
        current_date = fields.Date.context_today(self)
        data = self.env["fleet.vehicle.log.contract"]._read_group(
            domain=[
                ("expiration_date", "!=", False),
                ("vehicle_id", "in", self.ids),
                ("state", "!=", "closed"),
            ],
            groupby=["vehicle_id", "state"],
            aggregates=["expiration_date:max"],
        )

        prepared_data = {}
        for vehicle_id, state, expiration_date in data:
            if prepared_data.get(vehicle_id.id):
                if prepared_data[vehicle_id.id]["expiration_date"] < expiration_date:
                    prepared_data[vehicle_id.id]["expiration_date"] = expiration_date
                    prepared_data[vehicle_id.id]["state"] = state
            else:
                prepared_data[vehicle_id.id] = {
                    "state": state,
                    "expiration_date": expiration_date,
                }

        for record in self:
            vehicle_data = prepared_data.get(record.id)
            if vehicle_data:
                diff_time = (vehicle_data["expiration_date"] - current_date).days
                record.contract_renewal_overdue = diff_time < 0
                record.contract_renewal_due_soon = (
                    not record.contract_renewal_overdue
                    and (diff_time < delay_alert_contract)
                )
                record.contract_state = vehicle_data["state"]
            else:
                record.contract_renewal_overdue = False
                record.contract_renewal_due_soon = False
                record.contract_state = ""

    def _get_analytic_name(self):
        # Overridden in l10n_be_hr_payroll_fleet
        return self.license_plate or _("No plate")

    def _search_contract_renewal_due_soon(self, operator, value):
        if operator != "in":
            return NotImplemented
        params = self.env["ir.config_parameter"].sudo()
        delay_alert_contract = int(
            params.get_param("hr_fleet.delay_alert_contract", default=30)
        )
        today = fields.Date.context_today(self)
        datetime_today = fields.Datetime.from_string(today)
        limit_date = fields.Datetime.to_string(
            datetime_today + relativedelta(days=+delay_alert_contract)
        )
        return [
            (
                "log_contracts",
                "any",
                [
                    ("expiration_date", ">", today),
                    ("expiration_date", "<", limit_date),
                    ("state", "in", ["open", "expired"]),
                ],
            )
        ]

    def _search_contract_renewal_overdue(self, operator, value):
        if operator != "in":
            return NotImplemented
        today = fields.Date.context_today(self)
        # get the id of vehicles that have overdue contracts
        # but exclude those for which a new contract has already been created for them
        return [
            (
                "log_contracts",
                "any",
                [
                    ("expiration_date", "!=", False),
                    ("expiration_date", "<", today),
                    ("state", "in", ["open", "expired"]),
                ],
            ),
            "!",
            (
                "log_contracts",
                "any",
                [
                    ("expiration_date", "!=", False),
                    ("expiration_date", ">=", today),
                    ("state", "in", ["open", "futur"]),
                ],
            ),
        ]

    @api.model_create_multi
    def create(self, vals_list):
        to_update_drivers_cars = set()
        to_update_drivers_bikes = set()
        state_waiting_list = self.env.ref(
            "fleet.fleet_vehicle_state_waiting_list", raise_if_not_found=False
        )
        for vals in vals_list:
            if vals.get("future_driver_id"):
                state_id = vals.get("state_id")
                if not state_waiting_list or state_waiting_list.id != state_id:
                    future_driver = vals["future_driver_id"]
                    if vals.get("vehicle_type") == "bike":
                        to_update_drivers_bikes.add(future_driver)
                    elif vals.get("vehicle_type") == "car":
                        to_update_drivers_cars.add(future_driver)
        if to_update_drivers_cars:
            self.search(
                [
                    ("driver_id", "in", to_update_drivers_cars),
                    ("vehicle_type", "=", "car"),
                ]
            ).plan_to_change_car = True
        if to_update_drivers_bikes:
            self.search(
                [
                    ("driver_id", "in", to_update_drivers_bikes),
                    ("vehicle_type", "=", "bike"),
                ]
            ).plan_to_change_bike = True

        vehicles = super().create(vals_list)

        for vehicle, vals in zip(vehicles, vals_list, strict=False):
            if vals.get("driver_id"):
                vehicle.create_driver_history(vals)
        return vehicles

    def write(self, vals):
        if "odometer" in vals and any(
            vehicle.odometer > vals["odometer"] for vehicle in self
        ):
            raise UserError(
                _("The odometer value cannot be lower than the previous one.")
            )

        if vals.get("driver_id"):
            driver_id = vals["driver_id"]
            for vehicle in self.filtered(lambda v: v.driver_id.id != driver_id):
                vehicle.create_driver_history(vals)
                if vehicle.driver_id:
                    vehicle.activity_schedule(
                        "mail.mail_activity_data_todo",
                        user_id=vehicle.manager_id.id or self.env.user.id,
                        note=_("Specify the End date of %s", vehicle.driver_id.name),
                    )

        if vals.get("future_driver_id"):
            future_driver = vals["future_driver_id"]
            state_waiting_list = self.env.ref(
                "fleet.fleet_vehicle_state_waiting_list", raise_if_not_found=False
            )
            state_new_request = self.env.ref(
                "fleet.fleet_vehicle_state_new_request", raise_if_not_found=False
            )
            vehicle_types = set(
                self.filtered(
                    lambda vehicle: (
                        not state_waiting_list
                        or vals.get("state_id", vehicle.state_id.id)
                        not in [state_waiting_list.id, state_new_request.id]
                    )
                ).mapped("vehicle_type")
            )
            if vehicle_types:
                vehicle_read_group = dict(
                    self.env["fleet.vehicle"]._read_group(
                        domain=[
                            ("driver_id", "=", future_driver),
                            ("vehicle_type", "in", vehicle_types),
                            ("id", "not in", self.ids),
                        ],
                        groupby=["vehicle_type"],
                        aggregates=["id:recordset"],
                    )
                )
                if "bike" in vehicle_read_group:
                    vehicle_read_group["bike"].write({"plan_to_change_bike": True})
                if "car" in vehicle_read_group:
                    vehicle_read_group["car"].write({"plan_to_change_car": True})

        if "active" in vals and not vals["active"]:
            self.env["fleet.vehicle.log.contract"].search(
                [("vehicle_id", "in", self.ids)]
            ).active = False
            self.env["fleet.vehicle.log.services"].search(
                [("vehicle_id", "in", self.ids)]
            ).active = False

        return super().write(vals)

    def _get_driver_history_data(self, vals):
        self.check_singleton()
        return {
            "vehicle_id": self.id,
            "driver_id": vals["driver_id"],
            "date_start": fields.Date.today(),
        }

    def create_driver_history(self, vals):
        for vehicle in self:
            self.env["fleet.vehicle.assignation.log"].create(
                vehicle._get_driver_history_data(vals),
            )

    def action_accept_driver_change(self):
        # Find all the vehicles of the same type for which the driver is the future_driver_id
        # and remove their driver_id
        vehicles = self.search(
            [
                ("driver_id", "in", self.mapped("future_driver_id").ids),
                ("vehicle_type", "=", self.vehicle_type),
            ]
        )
        vehicles.write(
            {
                "driver_id": False,
                "plan_to_change_car": False,
                "plan_to_change_bike": False,
            }
        )

        for vehicle in self:
            vehicle.plan_to_change_bike = False
            vehicle.plan_to_change_car = False
            vehicle.driver_id = vehicle.future_driver_id
            vehicle.future_driver_id = False

    def return_action_to_open(self):
        """This opens the xml view specified in xml_id for the current vehicle"""
        self.check_singleton()
        xml_id = self.env.context.get("xml_id")
        if xml_id:
            res = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
                "fleet.%s" % xml_id
            )
            res.update(
                context=dict(
                    self.env.context, default_vehicle_id=self.id, group_by=False
                ),
                domain=[("vehicle_id", "=", self.id)],
            )
            return res
        return False

    def act_show_log_cost(self):
        """This opens log view to view and add new log for this vehicle, groupby default to only show effective costs
        @return: the costs log view
        """
        self.check_singleton()
        copy_context = dict(self.env.context)
        copy_context.pop("group_by", None)
        res = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "fleet.fleet_vehicle_costs_action"
        )
        res.update(
            context=dict(
                copy_context,
                default_vehicle_id=self.id,
                search_default_parent_false=True,
            ),
            domain=[("vehicle_id", "=", self.id)],
        )
        return res

    def _track_subtype(self, init_values):
        self.check_singleton()
        if "driver_id" in init_values or "future_driver_id" in init_values:
            return self.env.ref("fleet.mt_fleet_driver_updated")
        return super()._track_subtype(init_values)

    def open_assignation_logs(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": "Assignment Logs",
            "view_mode": "list",
            "res_model": "fleet.vehicle.assignation.log",
            "domain": [("vehicle_id", "=", self.id)],
            "context": {
                "default_driver_id": self.driver_id.id,
                "default_vehicle_id": self.id,
            },
        }

    def action_send_email(self):
        return {
            "name": _("Send Email"),
            "type": "ir.actions.act_window",
            "target": "new",
            "view_mode": "form",
            "res_model": "fleet.vehicle.send.mail",
            "context": {
                "default_vehicle_ids": self.ids,
            },
        }

    def action_view_odometer_report(self):
        self.check_singleton()
        action = self.env["ir.actions.actions"]._get_action_dict_by_xml_id(
            "fleet.fleet_vehicle_odometer_reporting_action"
        )
        action.update(
            {
                "domain": [("vehicle_id", "=", self.id)],
                "context": {"search_default_groupby_date": True},
            }
        )
        return action
