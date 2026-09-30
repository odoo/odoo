# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Property Offer'
    _order = 'price desc'

    price = fields.Float()
    status = fields.Selection([
        ('accepted', 'Accepted'),
        ('refused', 'Refused'),
    ], copy=False)
    partner_id = fields.Many2one('res.partner', required=True)
    property_id = fields.Many2one('estate.property', required=True, ondelete='cascade')
    property_type_id = fields.Many2one(related='property_id.property_type_id', store=True)
    validity = fields.Integer(default=7)
    date_deadline = fields.Date(compute='_compute_date_deadline', inverse='_inverse_date_deadline')

    _check_price = models.Constraint('CHECK(price > 0)', 'Offer price must be positive.')

    @api.depends('create_date', 'validity')
    def _compute_date_deadline(self):
        for offer in self:
            start_date = fields.Date.to_date(offer.create_date) or fields.Date.today()
            offer.date_deadline = start_date + timedelta(days=offer.validity)

    def _inverse_date_deadline(self):
        for offer in self:
            if offer.date_deadline:
                start_date = fields.Date.to_date(offer.create_date) or fields.Date.today()
                offer.validity = (offer.date_deadline - start_date).days

    def action_accept(self):
        self.ensure_one()
        property_record = self.property_id
        if property_record.state in ('sold', 'cancelled'):
            raise UserError(self.env._('A sold or cancelled property cannot accept offers.'))
        if property_record.offer_ids.filtered(lambda offer: offer.status == 'accepted' and offer != self):
            raise UserError(self.env._('Another offer has already been accepted.'))
        self.status = 'accepted'
        property_record.write({
            'partner_id': self.partner_id.id,
            'selling_price': self.price,
            'state': 'offer_accepted',
        })
        return True

    def action_refuse(self):
        self.ensure_one()
        if self.status == 'accepted':
            raise UserError(self.env._('An accepted offer cannot be refused.'))
        self.status = 'refused'
        return True
