from odoo import api, fields, models
from odoo.osv.expression import AND


class ProductAttribute(models.Model):
    _name = 'product.attribute'
    _inherit = ['product.attribute', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name', 'display_type', 'template_value_ids', 'attribute_line_ids', 'create_variant']


class ProductAttributeCustomValue(models.Model):
    _name = 'product.attribute.custom.value'
    _inherit = ["product.attribute.custom.value", "pos.load.mixin"]

    pos_order_line_id = fields.Many2one('pos.order.line', string="PoS Order Line", ondelete='cascade')

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_line_id', 'in', [line['id'] for line in data['pos.order.line']])]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['pos.order.line']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['custom_value', 'custom_product_template_attribute_value_id', 'pos_order_line_id', 'write_date']


class ProductTemplateAttributeLine(models.Model):
    _name = 'product.template.attribute.line'
    _inherit = ['product.template.attribute.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['display_name', 'attribute_id', 'product_template_value_ids']

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
    def _load_pos_data_domain(self, data):
        ptav_ids = data['product.product'].product_template_variant_value_ids.ids + data['product.template.attribute.line'].product_template_value_ids.ids
        product_attribute_ids = data['product.attribute'].ids
        return AND([
            [('ptav_active', '=', True)],
            [('attribute_id', 'in', product_attribute_ids)],
            [('id', 'in', list(ptav_ids))]
        ])

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.attribute']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['attribute_id', 'attribute_line_id', 'product_attribute_value_id', 'price_extra', 'name', 'is_custom', 'html_color', 'image', 'exclude_for']

class ProductTemplateAttributeExclusion(models.Model):
    _name = 'product.template.attribute.exclusion'
    _inherit = ['product.template.attribute.exclusion', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        loaded_product_tmpl_ids = data['product.template'].ids
        loaded_ptav_ids = data['product.template.attribute.value'].ids
        return [('product_tmpl_id', 'in', loaded_product_tmpl_ids), ('product_template_attribute_value_id', 'in', loaded_ptav_ids)]

    @api.model
    def _load_pos_data_dependencies(self):
        return ['product.template', 'product.template.attribute.value']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['value_ids', 'product_template_attribute_value_id']
