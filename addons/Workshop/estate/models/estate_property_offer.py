from odoo import api, models, fields
from odoo.exceptions import UserError

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Offers on estate properties"

    price = fields.Float()
    partner_id = fields.Many2one("res.partner", required=True)
    property_id = fields.Many2one("estate.property", required=True)
    state = fields.Selection(selection=[("accepted", "Accepted"), ("refused", "Refused")])

    _check_offer_price = models.Constraint("CHECK(price > 0)", "The offer price must be strictly positive")

    def accept_offer(self):
        for record in self:
            if record.state == "refused":
                raise UserError("You cannot accept a refused offer")
            elif record.property_id.state == "offer_accepted":
                raise UserError("this property already has an accepted offer")
            else:
                record.state = "accepted"
                record.property_id.buyer_id = record.partner_id
                record.property_id.state = "offer_accepted"
                record.property_id.selling_price = record.price

    def refuse_offer(self):
        for record in self:
            if record.state == "accepted":
                raise UserError("You cannot refuse an accepted offer")
            else:
                record.state = "refused"