from odoo import models, fields, api

class MarketplaceSeller(models.Model):
    _name = 'marketplace.seller'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Marketplace Seller'

    name = fields.Char(
        string='Name', required=True, tracking=True,
        )
    phone = fields.Char(string='Phone')
    email = fields.Char(string='Email', required=True)
    is_approved = fields.Boolean(string='Approved', default=False)

    street = fields.Char(string='Street')
    city = fields.Char(string='City')
    zip = fields.Char(string='ZIP Code')

