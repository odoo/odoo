from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokCategory(models.Model):
    _name = 'tiktok.category'
    _description = 'Tiktok Category'

    name = fields.Char('Name')
    # complete_name = fields.Char(compute='_complete_name', string='Name')
    
    tiktok_category_id = fields.Integer('Tiktok Category ID')
    tiktok_parent_id = fields.Integer('Tiktok Parent ID')

    # is_lowest_child = fields.Boolean(compute='_is_lowest_child', string='Lowest Child', default=False, store=True)
    child_ids = fields.One2many('tiktok.category', 'parent_id', 'Child')
    parent_id = fields.Many2one('tiktok.category', 'Parent')