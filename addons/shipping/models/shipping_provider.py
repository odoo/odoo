# -*- coding: utf-'8' "-*-"

from openerp import models, fields 

class ShippingProvider(models.Model):
    """
    """
    _name='shipping.provider'
    _description = 'Shipping Provider'

    name = fields.Char(string='Name',required=True)
    environment = fields.Selection([('test','Test'),('prod','Prod')], default='test')
    website_published = fields.Boolean(string='Visible in Portal / Website',default=True)

    company_id = fields.Many2one('res.company',string='Company',required=True)


class ShippingTransaction(models.Model):
    """
    """
    _name='shipping.transaction'
    _description = 'Shipping Transaction'
    
    reference = fields.Char(string='Order Reference', required=True)
    description = fields.Text(string='Description')

    shipper_id = fields.Many2one('res.partner',string='Recipient')
    shipper_name = fields.Char(string='Recipient Name')
    shipper_address = fields.Char(string='Address')
    shipper_email = fields.Char(string='Email')
    shipper_lang = fields.Char(string='Lang')
    shipper_zip = fields.Char(string='Zip')
    shipper_city = fields.Char(string='City')
    shipper_phone = fields.Char(string='Phone')
    shipper_country_id = fields.Many2one('res.country','Country')

    recipient_id = fields.Many2one('res.partner',string='Recipient')
    recipient_name = fields.Char(string='Recipient Name')
    recipient_address = fields.Char(string='Address')
    recipient_email = fields.Char(string='Email')
    recipient_lang = fields.Char(string='Lang')
    recipient_zip = fields.Char(string='Zip')
    recipient_city = fields.Char(string='City')
    recipient_phone = fields.Char(string='Phone')
    recipient_country_id = fields.Many2one('res.country','Country')

    payment_method = fields.Selection([('shipper','Shipper'),('recipient','Recipient')])

    currency_id = fields.Many2one('res.currency',string='Currency',required=True)
    provider_id = fields.Many2one('shipping.provider',string='Shipping Provider',required=True)
    tracking_number = fields.Char(string='Tracking N°')