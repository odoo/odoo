from odoo import models, fields

class RestaurantOrder(models.Model):
    _name = 'restaurant.order'
    _description = 'Restaurant Order'

    table_id = fields.Integer(string='Table Number')
    menu_item_ids = fields.Many2many('restaurant.menu', string='Menu Items')
    total_price = fields.Float(string='Total Price')
    status = fields.Selection([('draft', 'Draft'), ('confirmed', 'Confirmed'), ('paid', 'Paid')], string='Status', default='draft')
