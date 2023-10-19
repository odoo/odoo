from odoo import models, fields

class Company(models.Model):
    _name = "company"
    _description = "Description of the Company model"
    eic_code = fields.Char(string='EIC Code')
    name = fields.Char(string='Company Name')
    address = fields.Char(string='Address')
    country = fields.Char()
    email = fields.Char(string='Email')
    representative = fields.Char(string='Representative')
    vat = fields.Char(string='VAT Code')
    nav_code = fields.Char(string='Nav Code')
    meter_sn = fields.Char(string='Meter Serial Number')
    delivery_point = fields.Char(string='Delivery Point')
    comp_function = fields.Char(string='Function')

    role = fields.Selection([('customer', 'Customer'), ('gen', 'Gen'),('trade', 'Trade')
                             ], 'Role'
                             )
    voltage_id = fields.Many2one('voltage', string='Voltage')
