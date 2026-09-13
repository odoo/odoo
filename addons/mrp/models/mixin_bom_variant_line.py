from odoo import fields, models


class MixinBomVariantLine(models.AbstractModel):
    _name = "mixin.bom.variant.line"
    _description = "BoM row that may be restricted to some variants"

    bom_id = fields.Many2one(
        comodel_name="mrp.bom",
        string="Parent BoM",
        index=True,
        required=True,
        ondelete="cascade",
    )
    possible_bom_product_template_attribute_value_ids = fields.Many2many(
        related="bom_id.possible_product_template_attribute_value_ids"
    )
    bom_product_template_attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        string="Apply on Variants",
        domain="[('id', 'in', possible_bom_product_template_attribute_value_ids)]",
        ondelete="restrict",
        help="BOM Product Variants needed to apply this line.",
    )

    def _is_bom_line_skipped(self, product, never_attribute_values=False):
        self.check_singleton()
        if not product or product._name == "product.template":
            return False
        return self.env["mrp.bom"]._is_skipped_for_no_variant(
            product,
            self.bom_product_template_attribute_value_ids,
            never_attribute_values,
        )
