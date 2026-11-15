# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare


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

    @api.model_create_multi
    def create(self, vals_list):
        property_ids = {vals['property_id'] for vals in vals_list if vals.get('property_id')}
        properties = self.env['estate.property'].browse(list(property_ids))
        highest_prices = {
            property_record.id: max(property_record.offer_ids.mapped('price'), default=0.0)
            for property_record in properties
        }
        for vals in vals_list:
            property_record = properties.filtered(lambda record: record.id == vals.get('property_id'))
            if not property_record:
                continue
            if property_record.state in ('offer_accepted', 'sold', 'cancelled'):
                raise UserError(self.env._('A closed property cannot receive offers.'))
            price = vals.get('price', 0.0)
            if float_compare(price, highest_prices[property_record.id], precision_digits=2) < 0:
                raise UserError(self.env._('An offer must not be lower than an existing offer.'))
            highest_prices[property_record.id] = max(price, highest_prices[property_record.id])
        offers = super().create(vals_list)
        offers.mapped('property_id').write({'state': 'offer_received'})
        return offers

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
