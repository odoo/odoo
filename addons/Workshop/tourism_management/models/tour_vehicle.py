from odoo import api, models, fields


class TourVehicle(models.Model):
    _name = "tour.vehicle"
    _description = "Tour Vehicle"

    name = fields.Char(required=True)
    vehicle_type = fields.Selection(
        selection=[
            ("bus", "Bus"),
            ("minibus", "Minibus"),
            ("van", "Van"),
            ("luxury_car", "Luxury Car"),
        ],
        required=True,
        default="van",
    )
    plate_number = fields.Char(required=True)
    capacity = fields.Integer(required=True)
    driver_name = fields.Char()
    driver_phone = fields.Char()
    active = fields.Boolean(default=True)
    assignment_ids = fields.One2many("tour.transport.assignment", "vehicle_id", string="Transport Assignments")
    utilization_count = fields.Integer(compute="_compute_utilization_count", store=True)

    _check_capacity = models.Constraint(
        "CHECK(capacity > 0)",
        "The vehicle capacity must be strictly positive.",
    )
    _unique_plate_number = models.Constraint(
        "UNIQUE(plate_number)",
        "This plate number is already assigned to another vehicle.",
    )

    @api.depends("assignment_ids.status")
    def _compute_utilization_count(self):
        for vehicle in self:
            vehicle.utilization_count = len(vehicle.assignment_ids.filtered(lambda a: a.status != "cancelled"))
