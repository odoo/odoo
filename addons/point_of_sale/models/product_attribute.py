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

    pos_order_line_id = fields.Many2one('pos.order.line', string="PoS Order Line", ondelete='cascade', index='btree_not_null')

    @api.model
    def _load_pos_data_domain(self, data, config):
        return [('pos_order_line_id', 'in', [line['id'] for line in data['pos.order.line']])]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['custom_value', 'custom_product_template_attribute_value_id', 'pos_order_line_id', 'write_date']


class ProductTemplateAttributeLine(models.Model):
    _name = 'product.template.attribute.line'
    _inherit = ['product.template.attribute.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config):
        return ['display_name', 'attribute_id', 'product_template_value_ids']

    @api.model
    def _load_pos_data_domain(self, data, config):
        loaded_product_tmpl_ids = list({p['id'] for p in data['product.template']})
        return [('product_tmpl_id', 'in', loaded_product_tmpl_ids)]


class ProductTemplateAttributeValue(models.Model):
    _name = 'product.template.attribute.value'
    _inherit = ['product.template.attribute.value', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        ptav_ids = {ptav_id for p in data['product.product'] for ptav_id in p['product_template_variant_value_ids']}
        ptav_ids.update({ptav_id for ptal in data['product.template.attribute.line'] for ptav_id in ptal['product_template_value_ids']})
        return [
            ('ptav_active', '=', True),
            ('attribute_id', 'in', [attr['id'] for attr in data['product.attribute']]),
            ('id', 'in', list(ptav_ids)),
        ]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['attribute_id', 'attribute_line_id', 'product_attribute_value_id', 'price_extra', 'name', 'is_custom', 'html_color', 'image', 'exclude_for']


class ProductTemplateAttributeExclusion(models.Model):
    _name = 'product.template.attribute.exclusion'
    _inherit = ['product.template.attribute.exclusion', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data, config):
        loaded_product_tmpl_ids = list({p['id'] for p in data['product.template']})
        return [('product_tmpl_id', 'in', loaded_product_tmpl_ids)]

    @api.model
    def _load_pos_data_fields(self, config):
        return ['value_ids']
