from odoo import models, fields

class PriceComponents(models.Model):
    _name = "price_components"
    _description = "Description of the Price Componenets model"
    name = fields.Char()
    code = fields.Char()
    group = fields.Selection([('other', 'OTHER'), ('ost', 'OST Fees'),('distribution', 'Distribution Fees'),('partner', 'Partner Fees')],string='Price Group')
    type = fields.Selection([('volume', 'Volume'), ('fixed', 'Fixed')],string='Type')
    currency_id = fields.Many2one('res.currency', string='Currency')
    
