from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokCategory(models.Model):
    _name = 'tiktok.category'
    _description = 'Tiktok Category'

    name = fields.Char('Name')    
    tiktok_category_id = fields.Integer('Category ID')
    tiktok_parent_id = fields.Integer('Parent ID')
    is_leaf = fields.Boolean('Leaf Category')
    permission_statuses = fields.Char('Permission')

    rules_ids = fields.One2many('tiktok.category.rules', 'tiktok_category_id', 'Rules')

class TiktokCategoryRules(models.Model):
    _name = 'tiktok.category.rules'
    _description = 'Tiktok Category Rules'

    name = fields.Char('Name')    
    tiktok_category_id = fields.Many2one('tiktok.category','Category ID')
    cod = fields.Boolean('COD Supported')
    epr = fields.Boolean('EPR Required')
    package_dimension = fields.Boolean('Package Dimension Required')
    size_sup = fields.Boolean('Size Chart Supported')
    size_req = fields.Boolean('Size Chart Required')
    certif_id = fields.Char('Certification ID')
    certif_req = fields.Boolean('Certification Required')
    url = fields.Char('Sample Certification')

