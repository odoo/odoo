from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class TiktokAttribute(models.Model):
    _name = 'tiktok.attribute'
    _description = 'Tiktok Attribute'

    name = fields.Char('Name')
    attribute_type = fields.Char('Type')
    category_id = fields.Many2one('tiktok.category', 'Category')
    is_customizable = fields.Boolean('Customizable')
    is_multiple_selection = fields.Boolean('Multiple Selection')
    is_requried = fields.Boolean('Requried')
    attribute_id = fields.Char('Attribute ID')
    value_ids = fields.One2many('tiktok.attribute.value', 'attribute_id', 'Values')

class TiktokAttributeValue(models.Model):
    _name = 'tiktok.attribute.value'
    _description = 'Tiktok Attribute Value'

    name = fields.Char('Name')
    value_id = fields.Char('Value ID')
    attribute_id = fields.Many2one('tiktok.attribute', 'Attribute')
    