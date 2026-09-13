from odoo import api, fields, models


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    visibility = fields.Selection(
        selection=[("visible", "Visible"), ("hidden", "Hidden")],
        default="visible",
    )
    preview_variants = fields.Selection(
        selection=[
            ("visible", "Visible"),
            ("hidden", "Hidden"),
            ("hover", "Hover"),
        ],
        string="On Product Cards",
        default="hidden",
        help="Instantly created variants are available for selection from your /shop page.",
    )
    is_thumbnail_visible = fields.Boolean(
        string="Show Thumbnails",
        help="Use product variant images instead of the attribute values displays.",
    )

    @api.onchange("create_variant", "display_type")
    def _onchange_disable_preview_variants(self):
        if self.create_variant != "always" or self.display_type == "multi":
            self.preview_variants = "hidden"
            self.is_thumbnail_visible = False
