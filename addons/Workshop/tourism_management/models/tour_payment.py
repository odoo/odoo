from odoo import models, fields
from odoo.exceptions import UserError


class TourPayment(models.Model):
    _name = "tour.payment"
    _description = "Tour Payment"

    booking_id = fields.Many2one("tour.booking", required=True, ondelete="cascade")
    amount = fields.Float(required=True)
    payment_method = fields.Selection(
        selection=[
            ("cash", "Cash"),
            ("card", "Card"),
            ("bank_transfer", "Bank Transfer"),
            ("online", "Online"),
        ],
        required=True,
        default="cash",
    )
    payment_date = fields.Date(default=fields.Date.context_today, required=True)
    state = fields.Selection(
        selection=[("draft", "Draft"), ("confirmed", "Confirmed"), ("refunded", "Refunded")],
        default="draft",
        required=True,
    )
    reference = fields.Char()

    _check_amount = models.Constraint(
        "CHECK(amount > 0)",
        "The payment amount must be strictly positive.",
    )

    def action_confirm(self):
        for payment in self:
            if payment.state != "draft":
                raise UserError("Only draft payments can be confirmed.")
            payment.state = "confirmed"
        self.mapped("booking_id")._update_payment_status()

    def action_refund(self):
        for payment in self:
            if payment.state != "confirmed":
                raise UserError("Only confirmed payments can be refunded.")
            payment.state = "refunded"
        self.mapped("booking_id")._update_payment_status()
