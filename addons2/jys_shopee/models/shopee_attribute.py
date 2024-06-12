from odoo import api, fields, models, tools, _
from odoo.exceptions import UserError, ValidationError

class ShopeeAttribute(models.Model):
    _name = 'shopee.attribute'
    _description = 'Shopee Attribute'

    name = fields.Char('Name')
    input_type = fields.Char('Input Type')
    attribute_type = fields.Char('Attribute Type')
    
    value_ids = fields.One2many('shopee.attribute.value', 'attribute_id', 'Values')
    category_id = fields.Many2one('shopee.category', 'Category')
    is_mandatory = fields.Boolean('Mandatory', default=False)
    attribute_id = fields.Integer('Attribute ID')

class ShopeeAttributeValue(models.Model):
    _name = 'shopee.attribute.value'
    _description = 'Shopee Attribute Value'

    name = fields.Char('Name')
    attribute_id = fields.Many2one('shopee.attribute', 'Attribute')
    