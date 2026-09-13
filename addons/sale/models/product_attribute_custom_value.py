from odoo import fields, models


class ProductAttributeCustomValue(models.Model):
    _inherit = "product.attribute.custom.value"

    sale_order_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Sales Order Line",
        index="btree_not_null",
        ondelete="cascade",
    )

    _sol_custom_value_unique = models.UniqueIndex(
        "(custom_product_template_attribute_value_id, sale_order_line_id) "
        "WHERE sale_order_line_id IS NOT NULL",
        "Only one Custom Value is allowed per Attribute Value per Sales Order Line.",
    )
