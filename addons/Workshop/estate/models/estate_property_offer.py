from odoo import models,fields
from odoo.exceptions import UserError

class EstatePropertyOffer(models.Model):
    _name = "estate.property.offer"
    _description = "Estate Property Offers"

    price = fields.Float()
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True)
    status = fields.Selection(selection=[('accepted','Accepted'),('refused','Refused')])
    property_type_id = fields.Many2one('estate.property.type', related='property_id.property_type_id', store=True)

    def accept_property(self):
        for record in self:
            if record.property_id.offer_ids.filtered(lambda x:x.status == "accepted"):
                raise UserError("An offer has already been accepted for this property!")
            record.status = 'accepted'
            record.property_id.write({
                "buyer_id" : record.partner_id.id,
                "selling_price" : record.price,
                "state" : "offer_accepted"
            })
    

    def refuse_property(self):
        for record in self:
            if record.status == 'accepted':
                raise UserError("Accepted properties cannot be refused!")
            else:
                record.status = 'refused'

    
    _check_offer_price = models.Constraint(
        'CHECK(price > 0)',
        'The offer price must be strictly positive'
    )