from odoo import fields, models


class EstatePropertyOffer(models.Model):
    _name = 'estate.property.offer'
    _description = 'Offers for Estate Property'

    price = fields.Float(required=True)
    status = fields.Selection(
        copy=False,
        selection=[
            ('accepted', 'Accepted'),
            ('refused', 'Refused'),
        ],
    )
    partner_id = fields.Many2one('res.partner', string='Partner', index=True, required=True)
    property_id = fields.Many2one('estate.property', string='Property', index=True, required=True)
