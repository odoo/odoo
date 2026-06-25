from odoo import models, fields


class TourCommission(models.Model):
    _name = "tour.commission"
    _description = "Taxi Partner Commission"

    booking_id = fields.Many2one("tour.booking", required=True)
    taxi_partner_id = fields.Many2one("tour.taxi.partner", required=True)
    transport_assignment_id = fields.Many2one("tour.transport.assignment", required=True, ondelete="cascade")
    commission_amount = fields.Float(required=True)
    state = fields.Selection(
        selection=[("pending", "Pending"), ("paid", "Paid")],
        default="pending",
        required=True,
    )

    def action_mark_paid(self):
        for commission in self:
            commission.state = "paid"
