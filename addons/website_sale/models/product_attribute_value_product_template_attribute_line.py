from odoo import fields, models


class ProductAttributeValueProductTemplateAttributeLine(models.Model):
    _name = 'product.attribute.value.product.template.attribute.line'
    _description = 'Used product attribute values on product templates.'
    _table = 'product_attribute_value_product_template_attribute_line_rel'
    _rec_name = 'product_attribute_value_id'

    attribute_id = fields.Many2one(
        'product.attribute',
        related="product_attribute_value_id.attribute_id",
        store=True,
        index=True,
        export_string_translation=False,
    )
    product_attribute_value_id = fields.Many2one(
        'product.attribute.value',
        required=True,
        ondelete='cascade',
        index=True,
        export_string_translation=False,
    )
    product_template_attribute_line_id = fields.Many2one(
        'product.template.attribute.line',
        required=True,
        ondelete='cascade',
        index=True,
        export_string_translation=False,
    )

    _check_no_duplicate = models.Constraint(
        'UNIQUE(product_attribute_value_id, product_template_attribute_line_id)',
        'You can only have an attribute value on a product once',
    )
