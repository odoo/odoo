from odoo import api, fields, models
from odoo.osv.expression import AND


class ProductAttribute(models.Model):
    _inherit = ['product.attribute', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['name', 'display_type', 'template_value_ids', 'attribute_line_ids', 'create_variant']


class ProductAttributeCustomValue(models.Model):
    _inherit = ["product.attribute.custom.value", "pos.load.mixin"]

    pos_order_line_id = fields.Many2one('pos.order.line', string="PoS Order Line", ondelete='cascade')

    @api.model
    def _load_pos_data_domain(self, data):
        return [('pos_order_line_id', 'in', [line['id'] for line in data['pos.order.line']['data']])]

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['custom_value', 'custom_product_template_attribute_value_id', 'pos_order_line_id']


class ProductTemplateAttributeLine(models.Model):
    _inherit = ['product.template.attribute.line', 'pos.load.mixin']

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['display_name', 'attribute_id', 'product_template_value_ids']

    @api.model
    def _load_pos_data_domain(self, data):
        loaded_product_tmpl_ids = list({p['product_tmpl_id'] for p in data['product.product']['data']})
        return [('product_tmpl_id', 'in', loaded_product_tmpl_ids)]


class ProductTemplateAttributeValue(models.Model):
    _inherit = ['product.template.attribute.value', 'pos.load.mixin']

    @api.model
    def _load_pos_data_domain(self, data):
        loaded_product_tmpl_ids = list({p['product_tmpl_id'] for p in data['product.product']['data']})
        return AND([
            [('ptav_active', '=', True)],
            [('attribute_id', 'in', [attr['id'] for attr in data['product.attribute']['data']])],
            [('product_tmpl_id', 'in', loaded_product_tmpl_ids)]
        ])

    @api.model
    def _load_pos_data_fields(self, config_id):
        return ['attribute_id', 'attribute_line_id', 'product_attribute_value_id', 'price_extra', 'name', 'is_custom', 'html_color', 'image']
