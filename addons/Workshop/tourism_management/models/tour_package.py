from odoo import api, models, fields


class TourPackage(models.Model):
    _name = "tour.package"
    _description = "Tour Package"

    name = fields.Char(required=True)
    package_type = fields.Selection(
        selection=[
            ("city", "City Tour"),
            ("desert", "Desert Safari"),
            ("luxury", "Luxury"),
            ("family", "Family"),
            ("adventure", "Adventure"),
            ("cultural", "Cultural"),
            ("private", "Private"),
            ("group", "Group"),
        ],
        required=True,
        default="city",
    )
    destination_ids = fields.Many2many(
        "tour.destination",
        relation="tour_package_destination_rel",
        column1="package_id",
        column2="destination_id",
        string="Destinations",
    )
    duration_hours = fields.Float(string="Duration (Hours)")
    base_price = fields.Float(required=True)
    max_capacity = fields.Integer(required=True, default=10)
    description = fields.Text()
    active = fields.Boolean(default=True)
    booking_ids = fields.One2many("tour.booking", "package_id", string="Bookings")
    total_bookings = fields.Integer(compute="_compute_booking_stats", store=True)
    expected_revenue = fields.Float(compute="_compute_booking_stats", store=True)

    _check_max_capacity = models.Constraint(
        "CHECK(max_capacity > 0)",
        "The maximum capacity must be strictly positive.",
    )

    @api.depends("booking_ids.state", "booking_ids.total_amount")
    def _compute_booking_stats(self):
        for package in self:
            active_bookings = package.booking_ids.filtered(lambda b: b.state != "cancelled")
            package.total_bookings = len(active_bookings)
            package.expected_revenue = sum(active_bookings.mapped("total_amount"))
