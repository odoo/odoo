from odoo import _, api, fields, models
from odoo.exceptions import UserError


class FleetVehicleLogServices(models.Model):
    _name = "fleet.vehicle.log.services"
    _inherit = ["mixin.mail.thread", "mixin.mail.activity"]
    _rec_name = "service_type_id"
    _description = "Services for vehicles"

    active = fields.Boolean(default=True)
    vehicle_id = fields.Many2one(
        comodel_name="fleet.vehicle",
        index=True,
        required=True,
    )
    model_id = fields.Many2one(
        comodel_name="fleet.vehicle.model",
        related="vehicle_id.model_id",
        string="Model",
        store=True,
    )
    brand_id = fields.Many2one(
        comodel_name="fleet.vehicle.model.brand",
        related="vehicle_id.model_id.brand_id",
        string="Brand",
        store=True,
    )
    manager_id = fields.Many2one(
        comodel_name="res.users",
        related="vehicle_id.manager_id",
        string="Fleet Manager",
        store=True,
    )
    amount = fields.Monetary(string="Cost")
    description = fields.Char()
    odometer_id = fields.Many2one(
        comodel_name="fleet.vehicle.odometer",
        help="Odometer measure of the vehicle at the moment of this log",
    )
    odometer = fields.Float(
        string="Odometer Value",
        compute="_compute_odometer",
        inverse="_inverse_odometer",
        help="Odometer measure of the vehicle at the moment of this log",
    )
    odometer_unit = fields.Selection(
        related="vehicle_id.odometer_unit",
        string="Unit",
        readonly=True,
    )
    date = fields.Date(
        default=fields.Date.context_today,
        help="Date when the cost has been executed",
    )
    company_id = fields.Many2one(
        comodel_name="res.company",
        default=lambda self: self.env.company,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        related="company_id.currency_id",
    )
    purchaser_id = fields.Many2one(
        comodel_name="res.partner",
        string="Driver",
        compute="_compute_purchaser_id",
        store=True,
        readonly=False,
    )
    inv_ref = fields.Char(string="Vendor Reference")
    vendor_id = fields.Many2one(comodel_name="res.partner")
    notes = fields.Text()
    service_type_id = fields.Many2one(
        comodel_name="fleet.service.type",
        default=lambda self: self.env.ref(
            "fleet.type_service_service_7", raise_if_not_found=False
        ),
        required=True,
    )
    state = fields.Selection(
        selection=[
            ("new", "New"),
            ("running", "Running"),
            ("done", "Done"),
            ("cancelled", "Cancelled"),
        ],
        string="Stage",
        default="new",
        group_expand=True,
        tracking=True,
    )

    def _compute_odometer(self):
        self.odometer = 0
        for record in self:
            if record.odometer_id:
                record.odometer = record.odometer_id.value

    def _inverse_odometer(self):
        for record in self:
            if not record.odometer:
                raise UserError(
                    _("Emptying the odometer value of a vehicle is not allowed.")
                )
            odometer = self.env["fleet.vehicle.odometer"].create(
                {
                    "value": record.odometer,
                    "date": record.date or fields.Date.context_today(record),
                    "vehicle_id": record.vehicle_id.id,
                }
            )
            self.odometer_id = odometer

    @api.model_create_multi
    def create(self, vals_list):
        for data in vals_list:
            if "odometer" in data and not data["odometer"]:
                # if received value for odometer is 0, then remove it from the
                # data as it would result to the creation of a
                # odometer log with 0, which is to be avoided
                del data["odometer"]
        return super().create(vals_list)

    @api.depends("vehicle_id")
    def _compute_purchaser_id(self):
        for service in self:
            service.purchaser_id = service.vehicle_id.driver_id
