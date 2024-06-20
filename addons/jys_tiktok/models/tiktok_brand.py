from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokBrand(models.Model):
    _name = 'tiktok.brand'
    _description = 'Tiktok Brand'

    name = fields.Char('Name')    
    authorized_status = fields.Char('Auth Status')
    brand_id = fields.Char('Brand ID')
    is_t1_brand = fields.Boolean('T1 Brand')
    brand_status = fields.Char('Brand Status')
