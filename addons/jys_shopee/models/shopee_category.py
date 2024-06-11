from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ShopeeCategory(models.Model):
    _name = 'shopee.category'
    _description = 'Shopee Category'

    name = fields.Char('Name')
    # complete_name = fields.Char(compute='_complete_name', string='Name')
    
    shopee_category_id = fields.Integer('Shopee Category ID')
    shopee_parent_id = fields.Integer('Shopee Parent ID')

    # is_lowest_child = fields.Boolean(compute='_is_lowest_child', string='Lowest Child', default=False, store=True)
    child_ids = fields.One2many('shopee.category', 'parent_id', 'Child')
    parent_id = fields.Many2one('shopee.category', 'Parent')