from odoo import models, fields


class TourDestination(models.Model):
    _name = "tour.destination"
    _description = "Tour Destination"

    name = fields.Char(required=True)
    description = fields.Text()
    location = fields.Char()
    active = fields.Boolean(default=True)
    image = fields.Image(max_width=1024, max_height=1024)
    package_ids = fields.Many2many(
        "tour.package",
        relation="tour_package_destination_rel",
        column1="destination_id",
        column2="package_id",
        string="Packages",
    )
