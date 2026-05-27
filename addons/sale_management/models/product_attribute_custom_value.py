# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    sale_order_template_line_id = fields.Many2one(
        "sale.order.template.line",
        string="Quotation Template Line",
        index="btree_not_null",
        ondelete="cascade",
    )

    _sotl_custom_value_unique = models.Constraint(
        "unique(custom_product_template_attribute_value_id, sale_order_template_line_id)",
        "Only one Custom Value is allowed per Attribute Value per Quotation Template Line.",
    )
