# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = 'product.template'
    _check_company_auto = True

    @api.depends('attribute_line_ids.value_ids.is_custom', 'attribute_line_ids.attribute_id.create_variant')
    def _compute_has_configurable_attributes(self):
        """ A product is considered configurable if:
        - It has dynamic attributes
        - It has any attribute line with at least 2 attribute values configured
        - It has at least one custom attribute value """
        for product in self:
            product.has_configurable_attributes = (
                any(attribute.create_variant == 'dynamic' for attribute in product.attribute_line_ids.attribute_id)
                or any(len(attribute_line_id.value_ids) >= 2 for attribute_line_id in product.attribute_line_ids)
                or any(attribute_value.is_custom for attribute_value in product.attribute_line_ids.value_ids)
            )

class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    purchase_order_line_id = fields.Many2one('purchase.order.line', string="Purchase Order Line", required=False, ondelete='cascade')

    _sql_constraints = [
        ('pol_custom_value_unique', 'unique(custom_product_template_attribute_value_id, purchase_order_line_id)', "Only one Custom Value is allowed per Attribute Value per Purchase Order Line.")
    ]
