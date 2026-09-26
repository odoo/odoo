from uuid import uuid4
from odoo import api, fields, models


class ProductAttribute(models.Model):
    _name = 'product.attribute'
    _inherit = ['product.attribute', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['name', 'display_type', 'create_variant']


class ProductAttributeCustomValue(models.Model):
    _name = 'product.attribute.custom.value'
    _inherit = ["product.attribute.custom.value", "pos.load.mixin"]

    uuid = fields.Char(string='Uuid', readonly=True, default=lambda self: str(uuid4()), copy=False)
    pos_order_line_id = fields.Many2one('pos.order.line', string="PoS Order Line", ondelete='cascade', index='btree_not_null')

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_line_id', 'in', data['pos.order.line'].ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['pos.order.line']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['custom_value', 'custom_product_template_attribute_value_id', 'pos_order_line_id', 'write_date', 'uuid']


class ProductTemplateAttributeLine(models.Model):
    _name = 'product.template.attribute.line'
    _inherit = ['product.template.attribute.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['display_name', 'attribute_id', 'product_template_value_ids', 'active']

    @api.model
    def _load_pos_data_domain(self, data):
        return [('product_tmpl_id', 'in', data['product.template'].ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.template', 'product.template.attribute.value']


class ProductTemplateAttributeValue(models.Model):
    _name = 'product.template.attribute.value'
    _inherit = ['product.template.attribute.value', 'pos.load.mixin']

    @api.model
<<<<<<< 088a2b5d8125ac033ffd936cbe1e44830d013182
    def _load_pos_data_domain(self, data):
        ptav_ids = data['product.product'].product_template_variant_value_ids.ids + data['product.template.attribute.line'].product_template_value_ids.ids

||||||| 57fad2e46286b74d3832a3c7cea4a84327268224
    def _load_pos_data_domain(self, data, config):
        ptav_ids = {ptav_id for p in data['product.product'] for ptav_id in p['product_template_variant_value_ids']}
        ptav_ids.update({ptav_id for ptal in data['product.template.attribute.line'] for ptav_id in ptal['product_template_value_ids']})
=======
    def _load_pos_data_domain(self, data, config):
        ptav_ids = {ptav_id for p in data['product.product'] for ptav_id in p['product_template_variant_value_ids']}
        ptav_ids.update({ptav_id for ptal in data['product.template.attribute.line'] for ptav_id in ptal['product_template_value_ids']})
        # On an incremental load, data['product.attribute'] only holds the attributes
        # modified since the last sync, not all the loaded ones.
        attribute_domain = self.env['product.attribute']._load_pos_data_domain(data, config)
>>>>>>> 25086e16c2a910fb71f485e2f0a47e12a2f52f7b
        return [
            ('ptav_active', '=', True),
<<<<<<< 088a2b5d8125ac033ffd936cbe1e44830d013182
            ('attribute_id', 'in', data['product.attribute'].ids),
||||||| 57fad2e46286b74d3832a3c7cea4a84327268224
            ('attribute_id', 'in', [attr['id'] for attr in data['product.attribute']]),
=======
            ('attribute_id', 'any', attribute_domain),
>>>>>>> 25086e16c2a910fb71f485e2f0a47e12a2f52f7b
            ('id', 'in', list(ptav_ids)),
        ]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.attribute']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['attribute_id', 'attribute_line_id', 'product_attribute_value_id', 'price_extra', 'name', 'is_custom', 'html_color', 'image', 'excluded_value_ids']
