# type: ignore
from odoo import api, fields, models
from odoo.exceptions import UserError
from datetime import timedelta


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Real Estate Property Offer'
    _order = 'price desc'

    # Champs
    price = fields.Float(string="Offer Price", required=True)
    status = fields.Selection([
        ('accepted', 'Accepted'),
        ('refused', 'Refused')
    ], string="Status", required=True, default='refused')
    partner_id = fields.Many2one('res.partner', string="Buyer", required=True)
    property_id = fields.Many2one('estate.property', string="Property", required=True)
    validity = fields.Integer(default=7)
    date_deadline = fields.Date(
        compute="_compute_date_deadline",
        inverse="_inverse_date_deadline",
        store=True
    )

    property_type_id = fields.Many2one(
        related='property_id.property_type_id',
        store=True,
        readonly=True
    )

    # Contraintes SQL
    _sql_constraints = [
        ('check_offer_price_positive', 'CHECK(price > 0)', 'The offer price must be strictly positive.')
    ]

    # Méthodes calculées
    @api.depends("create_date", "validity")
    def _compute_date_deadline(self):
        for offer in self:
            create = offer.create_date or fields.Date.today()
            offer.date_deadline = create + timedelta(days=offer.validity)

    def _inverse_date_deadline(self):
        for offer in self:
            create = offer.create_date or fields.Date.today()
            offer.validity = (
                (offer.date_deadline - create.date()).days
                if offer.date_deadline else 0
            )

    # Actions personnalisées
    def action_accept(self):
        for offer in self:
            if offer.property_id.state == 'sold':
                raise UserError("You cannot accept an offer for a property that has already been sold")
            if offer.property_id.offer_ids.filtered(lambda o: o.status == 'accepted' and o.id != offer.id):
                raise UserError("You cannot accept an offer for a property that already has an accepted offer")
            offer.status = 'accepted'
            offer.property_id.write({
                'selling_price': offer.price,
                'buyer_id': offer.partner_id.id,
                'state': 'offer_accepted',
            })

    def action_refuse(self):
        for offer in self:
            offer.status = 'refused'
