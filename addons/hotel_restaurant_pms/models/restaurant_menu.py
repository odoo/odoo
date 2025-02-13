from odoo import models, fields

class RestaurantMenu(models.Model):
    _name = 'restaurant.menu'
    _description = 'Restaurant Menu'

    name = fields.Char(string='Item Name', required=True)
    price = fields.Float(string='Price')
    stock = fields.Integer(string='Stock Quantity')
