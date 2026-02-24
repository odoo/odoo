from odoo import models,fields

class Owner(models.Model):
    _name = "owner"

    name = fields.Char('Owner Name', required=True)
    phone = fields.Char('Phone Number')
    address = fields.Text('Address')
    property_ids = fields.One2many('property', 'owner_id', string='Properties Owned')