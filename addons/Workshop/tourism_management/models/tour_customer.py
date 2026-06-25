from odoo import api, models, fields


class TourCustomer(models.Model):
    _name = "tour.customer"
    _description = "Tour Customer"

    name = fields.Char(required=True)
    phone = fields.Char()
    email = fields.Char()
    nationality = fields.Char()
    passport_number = fields.Char()
    booking_ids = fields.One2many("tour.booking", "customer_id", string="Bookings")
    total_bookings = fields.Integer(compute="_compute_total_bookings", store=True)

    @api.depends("booking_ids.state")
    def _compute_total_bookings(self):
        for customer in self:
            customer.total_bookings = len(customer.booking_ids.filtered(lambda b: b.state != "cancelled"))
