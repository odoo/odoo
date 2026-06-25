from datetime import timedelta

from odoo import api, models, fields
from odoo.exceptions import UserError, ValidationError


class TourTransportAssignment(models.Model):
    _name = "tour.transport.assignment"
    _description = "Tour Transport Assignment"

    booking_id = fields.Many2one("tour.booking", required=True, ondelete="cascade")
    transport_type = fields.Selection(
        selection=[("internal", "Internal Vehicle"), ("taxi_partner", "Taxi Partner")],
        required=True,
        default="internal",
    )
    vehicle_id = fields.Many2one("tour.vehicle")
    taxi_partner_id = fields.Many2one("tour.taxi.partner")
    pickup_location = fields.Char()
    dropoff_location = fields.Char()
    pickup_time = fields.Datetime()
    status = fields.Selection(
        selection=[
            ("pending", "Pending"),
            ("assigned", "Assigned"),
            ("confirmed", "Confirmed"),
            ("completed", "Completed"),
            ("cancelled", "Cancelled"),
        ],
        default="pending",
        required=True,
    )
    commission_id = fields.Many2one("tour.commission", readonly=True, copy=False)

    @api.constrains("transport_type", "vehicle_id", "taxi_partner_id")
    def _check_transport_provider(self):
        for assignment in self:
            if assignment.transport_type == "internal" and not assignment.vehicle_id:
                raise ValidationError("An internal vehicle must be selected for an internal transport assignment.")
            if assignment.transport_type == "taxi_partner" and not assignment.taxi_partner_id:
                raise ValidationError("A taxi partner must be selected for a taxi partner transport assignment.")

    @api.constrains("vehicle_id", "pickup_time", "status")
    def _check_vehicle_double_booking(self):
        for assignment in self:
            if not assignment.vehicle_id or not assignment.pickup_time or assignment.status == "cancelled":
                continue
            day_start = assignment.pickup_time.replace(hour=0, minute=0, second=0, microsecond=0)
            conflicting = self.search(
                [
                    ("id", "!=", assignment.id),
                    ("vehicle_id", "=", assignment.vehicle_id.id),
                    ("status", "!=", "cancelled"),
                    ("pickup_time", ">=", day_start),
                    ("pickup_time", "<", day_start + timedelta(days=1)),
                ]
            )
            if conflicting:
                raise ValidationError(
                    "Vehicle %s is already assigned to another booking on %s."
                    % (assignment.vehicle_id.name, assignment.pickup_time.date())
                )

    @api.constrains("vehicle_id", "booking_id")
    def _check_vehicle_capacity(self):
        for assignment in self:
            if assignment.vehicle_id and assignment.booking_id.total_people > assignment.vehicle_id.capacity:
                raise ValidationError(
                    "Vehicle %s (capacity %s) cannot accommodate %s tourists."
                    % (assignment.vehicle_id.name, assignment.vehicle_id.capacity, assignment.booking_id.total_people)
                )

    def action_confirm_assignment(self):
        for assignment in self:
            if assignment.status not in ("pending", "assigned"):
                raise UserError("Only pending or assigned transport can be confirmed.")
            assignment.status = "confirmed"
            if assignment.transport_type == "taxi_partner" and not assignment.commission_id:
                commission = self.env["tour.commission"].create(
                    {
                        "booking_id": assignment.booking_id.id,
                        "taxi_partner_id": assignment.taxi_partner_id.id,
                        "transport_assignment_id": assignment.id,
                        "commission_amount": assignment.booking_id.total_amount
                        * assignment.taxi_partner_id.commission_rate
                        / 100.0,
                    }
                )
                assignment.commission_id = commission

    def action_complete_assignment(self):
        for assignment in self:
            if assignment.status != "confirmed":
                raise UserError("Only confirmed transport can be marked as completed.")
            assignment.status = "completed"

    def action_cancel_assignment(self):
        for assignment in self:
            assignment.status = "cancelled"
