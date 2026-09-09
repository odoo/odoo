from odoo import fields, models


class MixinProductVariantSelector(models.AbstractModel):
    _name = "mixin.product.variant.selector"
    _description = "Product Variant Selector Mixin"

    product_has_variants = fields.Boolean(
        string="Has variants", required=True, default=False
    )

    def _get_product_variant_selector_defaults(self, fields_list):
        """Resolve product_tmpl_id/product_id/product_has_variants from the
        default_product_id/default_product_tmpl_id context keys.

        Returns a (product_tmpl_id, vals) tuple: the resolved
        product.template record (possibly empty), and a dict of the
        default_get() values to merge in, gated the same way regardless of
        whether "product_id" was requested.
        """
        vals = {}
        product_tmpl_id = self.env["product.template"]
        if self.env.context.get("default_product_id"):
            product_id = self.env["product.product"].browse(
                self.env.context["default_product_id"]
            )
            product_tmpl_id = product_id.product_tmpl_id
            if "product_id" in fields_list:
                vals["product_tmpl_id"] = product_id.product_tmpl_id.id
                vals["product_id"] = product_id.id
        elif self.env.context.get("default_product_tmpl_id"):
            product_tmpl_id = self.env["product.template"].browse(
                self.env.context["default_product_tmpl_id"]
            )
            if "product_id" in fields_list:
                vals["product_tmpl_id"] = product_tmpl_id.id
                vals["product_id"] = product_tmpl_id.product_variant_id.id
                if len(product_tmpl_id.product_variant_ids) > 1:
                    vals["product_has_variants"] = True
        return product_tmpl_id, vals
