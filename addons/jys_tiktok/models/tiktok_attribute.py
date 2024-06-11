from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokAttribute(models.Model):
    _name = 'tiktok.attribute'
    _description = 'Tiktok Attribute'

    name = fields.Char('Name')
    input_type = fields.Char('Input Type')
    attribute_type = fields.Char('Attribute Type')
    
    value_ids = fields.One2many('tiktok.attribute.value', 'attribute_id', 'Values')
    category_id = fields.Many2one('tiktok.category', 'Category')
    is_mandatory = fields.Boolean('Mandatory', default=False)
    attribute_id = fields.Integer('Attribute ID')

class TiktokAttributeValue(models.Model):
    _name = 'tiktok.attribute.value'
    _description = 'Tiktok Attribute Value'

    name = fields.Char('Name')
    attribute_id = fields.Many2one('tiktok.attribute', 'Attribute')
    