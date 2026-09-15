from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.mixin_catalog import no_name_uniq_index


class ProductAttribute(models.Model):
    _name = "product.attribute"
    _inherit = "mixin.attribute"
    _description = "Product Attribute"
    _order = "sequence, id"
    _attribute_line_model = "product.template.attribute.line"

    _check_multi_checkbox_no_variant = models.Constraint(
        "CHECK(display_type != 'multi' OR create_variant = 'no_variant')",
        "Multi-checkbox display type is not compatible with the creation of variants",
    )
    _name_src_uniq = no_name_uniq_index()

    name = fields.Char(string="Attribute")
    active = fields.Boolean(
        help="If unchecked, it will allow you to hide the attribute without removing it."
    )
    sequence = fields.Integer(
        default=20,
        index=True,
        help="Determine the display order",
    )
    create_variant = fields.Selection(
        selection=[
            ("always", "Instantly"),
            ("dynamic", "Dynamically"),
            ("no_variant", "Never"),
        ],
        string="Variant Creation",
        default="always",
        required=True,
        help="""- Instantly: All possible variants are created as soon as the attribute and its values are added to a product.
        - Dynamically: Each variant is created only when its corresponding attributes and values are added to a sales order.
        - Never: Variants are never created for the attribute.
        Note: this cannot be changed once the attribute is used on a product.""",
    )
    display_type = fields.Selection(
        help="The display type used in the Product Configurator."
    )
    value_type = fields.Selection(
        default="multi",
        help="How many values a single attribute line may hold. Always 'multi' "
        "for products: a line carries every value the template offers.",
    )

    value_ids = fields.One2many(
        comodel_name="product.attribute.value",
        inverse_name="attribute_id",
        string="Values",
        copy=True,
    )
    template_value_ids = fields.One2many(
        comodel_name="product.template.attribute.value",
        inverse_name="attribute_id",
        string="Template Values",
    )
    attribute_line_ids = fields.One2many(
        comodel_name="product.template.attribute.line",
        inverse_name="attribute_id",
        string="Lines",
    )
    product_tmpl_ids = fields.Many2many(
        comodel_name="product.template",
        string="Related Products",
        compute="_compute_product_tmpl_ids",
        store=True,
    )
    count_product_tmpl = fields.Integer(compute="_compute_count_product_tmpl")

    def write(self, vals):
        if "create_variant" in vals:
            for pa in self:
                if (
                    vals["create_variant"] != pa.create_variant
                    and pa.count_product_tmpl
                ):
                    raise UserError(
                        _(
                            "You cannot change the Variants Creation Mode of the attribute %(attribute)s"
                            " because it is used on the following products:\n%(products)s",
                            attribute=pa.display_name,
                            products=", ".join(
                                pa.product_tmpl_ids.mapped("display_name")
                            ),
                        )
                    )
        invalidate = "sequence" in vals and any(
            record.sequence != vals["sequence"] for record in self
        )
        res = super().write(vals)
        if invalidate:
            self.env.flush_all()
            self.env.invalidate_all()
        return res

    def _filtered_used(self):
        return self.filtered("count_product_tmpl")

    def _usage_label(self):
        return ", ".join(self.product_tmpl_ids.mapped("display_name"))

    @api.depends("product_tmpl_ids")
    def _compute_count_product_tmpl(self):
        res = {
            attribute.id: count
            for attribute, count in self.env[
                "product.template.attribute.line"
            ]._read_group(
                domain=[
                    ("attribute_id", "in", self.ids),
                    ("product_tmpl_id.active", "=", True),
                ],
                groupby=["attribute_id"],
                aggregates=["__count"],
            )
        }
        for pa in self:
            pa.count_product_tmpl = res.get(pa.id, 0)

    @api.depends("attribute_line_ids.active", "attribute_line_ids.product_tmpl_id")
    def _compute_product_tmpl_ids(self):
        templates_by_attribute = {
            attribute.id: templates
            for attribute, templates in self.env[
                "product.template.attribute.line"
            ]._read_group(
                domain=[("attribute_id", "in", self.ids)],
                groupby=["attribute_id"],
                aggregates=["product_tmpl_id:recordset"],
            )
        }
        for pa in self:
            pa.with_context(
                active_test=False
            ).product_tmpl_ids = templates_by_attribute.get(pa.id, False)

    @api.onchange("display_type")
    def _onchange_display_type(self):
        if self.display_type == "multi" and self.count_product_tmpl == 0:
            self.create_variant = "no_variant"

    @api.readonly
    def action_view_product_template_attribute_lines(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": _("Products"),
            "res_model": "product.template.attribute.line",
            "view_mode": "list,form",
            "domain": [
                ("attribute_id", "=", self.id),
                ("product_tmpl_id.active", "=", True),
            ],
        }

    def _without_no_variant_attributes(self):
        return self.filtered(lambda pa: pa.create_variant != "no_variant")
