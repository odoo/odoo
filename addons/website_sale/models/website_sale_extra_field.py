# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models


class WebsiteSaleExtraField(models.Model):
    _name = "website.sale.extra.field"
    _description = "E-Commerce Extra Info Shown on product page"
    _order = "sequence"

    category_id = fields.Many2one(comodel_name="product.attribute.category")
    website_id = fields.Many2one(comodel_name="website", index="btree_not_null")
    sequence = fields.Integer(default=10)
    field_id = fields.Many2one(
        comodel_name="ir.model.fields",
        domain=[
            ("model_id.model", "=", "product.template"),
            ("ttype", "in", ["char", "binary", "float"]),
        ],
        required=True,
        ondelete="cascade",
    )
    label = fields.Char(related="field_id.field_description")
    name = fields.Char(related="field_id.name")

    def _get_values_for_display(self, product_variant, product_template):
        """Return non-empty product values to show for each extra field."""
        product_record = product_variant.sudo() if product_variant else product_template.sudo()
        display_values = {}
        for extra_field in self:
            display_value = product_record[extra_field.name]
            if display_value:
                display_values[extra_field] = display_value
        return display_values
