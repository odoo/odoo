from odoo import api, fields, models
from datetime import timedelta
from odoo.exceptions import UserError


class PropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offer"
    _order = "price desc"

    price = fields.Float()
    status = fields.Selection(
        [("accepted", "Accepted"), ("refused", "Refused")], copy=False
    )
    partner_id = fields.Many2one("res.partner", required=True)
    property_id = fields.Many2one("estate_property", string="Property", required=True)
    validity = fields.Integer(default=7)
    date_deadline = fields.Date(
        compute="_compute_date_deadline", inverse="_inverse_date_deadline"
    )
    property_type_id = fields.Many2one(
        "estate.property.type",
        related="property_id.property_type",
        store=True,
    )
    _sql_constraints = [
        (
            "check_offer_price",
            "CHECK(price >= 0)",
            "An offer price must be strictly positive",
        )
    ]

    # Set state to 'offer_received' when creating a new offer
    @api.model
    def create(self, vals):
        record = super().create(vals)
        # raise error if offer lower than existing offer
        if record.property_id.offer_ids.filtered(
            lambda o: o.price >= record.price and o.status == "accepted"
        ):
            raise UserError(
                "The offer price must be higher than the accepted offer price."
            )
        record.property_id.state = "offer_received"
        return record

    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for record in self:
            if record.create_date:  # Ensure create_date is set
                record.date_deadline = record.create_date.date() + timedelta(
                    days=record.validity
                )
            else:
                record.date_deadline = fields.Date.today() + timedelta(
                    days=record.validity
                )

    def _inverse_date_deadline(self):
        for record in self:
            if record.create_date and record.date_deadline:
                record.validity = (
                    record.date_deadline - record.create_date.date()
                ).days

    def action_offer_accept(self):
        for record in self:
            if record.property_id.offer_ids.filtered(lambda o: o.status == "accepted"):
                raise UserError("Only one offer can be accepted for a given property.")
            record.status = "accepted"
            record.property_id.state = "offer_accepted"
            record.property_id.partner_id = record.partner_id
            record.property_id.selling_price = record.price
        return True

    def action_offer_refuse(self):
        for record in self:
            record.status = "refused"
        return True
