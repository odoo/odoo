from odoo import models, fields


class StateProperty(models.Model):
    _name = 'state.property'
    _description = 'State Property'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    postCode = fields.Char(string='Post Code')
    date_available = fields.Date(string='Date Available')
    expected_price = fields.Float(string='Expected Price')
    selling_price = fields.Float(string='Selling Price')
    bedrooms = fields.Integer(string='Bedrooms')
    living_area = fields.Integer(string='Living Area')
    facades = fields.Integer(string='Facades')
    garage = fields.Boolean(string='Garage')
    garden = fields.Boolean(string='Garden')
    garden_area = fields.Integer(string='Garden Area')
    garden_orientation = fields.Selection([
        ('north', 'North'),
        ('south', 'South'),
        ('east', 'East'),
        ('west', 'West')
    ], string='Garden Orientation')


