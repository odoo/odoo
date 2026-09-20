from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Command

from .utils import unlink_where_possible


class ProductTemplateAttributeValue(models.Model):
    _name = "product.template.attribute.value"
    _inherit = ["mixin.color"]
    _description = "Product Template Attribute Value"
    _order = "attribute_line_id, product_attribute_value_id, id"

    ptav_active = fields.Boolean(
        string="Active",
        default=True,
    )
    name = fields.Char(
        related="product_attribute_value_id.name",
        string="Value",
    )

    product_attribute_value_id = fields.Many2one(
        comodel_name="product.attribute.value",
        string="Attribute Value",
        index=True,
        required=True,
        ondelete="cascade",
    )
    attribute_line_id = fields.Many2one(
        comodel_name="product.template.attribute.line",
        index=True,
        required=True,
        ondelete="cascade",
    )
    price_extra = fields.Float(
        string="Extra Price",
        min_display_digits="Product Price",
        default=0.0,
        help="Extra price for the variant with this attribute value on sale price."
        " eg. 200 price extra, 1000 + 200 = 1200.",
    )
    currency_id = fields.Many2one(
        related="attribute_line_id.product_tmpl_id.currency_id"
    )

    exclude_for = fields.One2many(
        comodel_name="product.template.attribute.exclusion",
        inverse_name="product_template_attribute_value_id",
        string="Exclude for",
        help="Make this attribute value not compatible with "
        "other values of the product or some attribute values of optional and accessory products.",
    )

    product_tmpl_id = fields.Many2one(
        related="attribute_line_id.product_tmpl_id",
    )
    attribute_id = fields.Many2one(  # noqa: E8529  One2many inverse of product.attribute.template_value_ids
        related="attribute_line_id.attribute_id",
        store=True,
        index=True,
    )
    ptav_product_variant_ids = fields.Many2many(
        comodel_name="product.product",
        relation="product_variant_combination",
        string="Related Variants",
        readonly=True,
    )

    html_color = fields.Char(
        related="product_attribute_value_id.html_color",
        string="HTML Color Index",
    )
    is_custom = fields.Boolean(related="product_attribute_value_id.is_custom")
    display_type = fields.Selection(related="product_attribute_value_id.display_type")
    color = fields.Integer(default=lambda self: self._default_color())
    image = fields.Image(related="product_attribute_value_id.image")

    _attribute_value_unique = models.Constraint(
        "unique(attribute_line_id, product_attribute_value_id)",
        "Each value should be defined only once per attribute per product.",
    )

    @api.constrains("attribute_line_id", "product_attribute_value_id")
    def _check_valid_values(self):
        for ptav in self:
            if (
                ptav.ptav_active
                and ptav.product_attribute_value_id
                not in ptav.attribute_line_id.value_ids
            ):
                raise ValidationError(
                    _(
                        "The value %(value)s is not defined for the attribute %(attribute)s"
                        " on the product %(product)s.",
                        value=ptav.product_attribute_value_id.display_name,
                        attribute=ptav.attribute_id.display_name,
                        product=ptav.product_tmpl_id.display_name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        if any("ptav_product_variant_ids" in v for v in vals_list):
            raise UserError(
                _(
                    "You cannot update related variants from the values. Please update related values from the variants."
                )
            )
        return super().create(vals_list)

    def write(self, values):
        if "ptav_product_variant_ids" in values:
            raise UserError(
                _(
                    "You cannot update related variants from the values. Please update related values from the variants."
                )
            )
        pav_in_values = "product_attribute_value_id" in values
        product_in_values = "product_tmpl_id" in values
        if pav_in_values or product_in_values:
            for ptav in self:
                if (
                    pav_in_values
                    and ptav.product_attribute_value_id.id
                    != values["product_attribute_value_id"]
                ):
                    raise UserError(
                        _(
                            "You cannot change the value of the value %(value)s set on product %(product)s.",
                            value=ptav.display_name,
                            product=ptav.product_tmpl_id.display_name,
                        )
                    )
                if (
                    product_in_values
                    and ptav.product_tmpl_id.id != values["product_tmpl_id"]
                ):
                    raise UserError(
                        _(
                            "You cannot change the product of the value %(value)s set on product %(product)s.",
                            value=ptav.display_name,
                            product=ptav.product_tmpl_id.display_name,
                        )
                    )
        res = super().write(values)
        if "exclude_for" in values:
            self.product_tmpl_id._create_variant_ids()
        return res

    def unlink(self):
        single_values = self.filtered(
            lambda ptav: len(ptav.attribute_line_id.product_template_value_ids) == 1
        )
        for ptav in single_values:
            ptav.ptav_product_variant_ids.write(
                {
                    "product_template_attribute_value_ids": [Command.unlink(ptav.id)],
                }
            )
        self.ptav_product_variant_ids._unlink_or_archive()

        self.env.flush_all()
        still_carried = self.filtered(
            lambda ptav: ptav.with_context(active_test=False).ptav_product_variant_ids
        )
        ptav_to_archive = still_carried | unlink_where_possible(
            self - still_carried, lambda ptavs: ptavs._unlink_without_fallback()
        )
        ptav_to_archive.write({"ptav_active": False})
        return True

    def _unlink_without_fallback(self):
        return super().unlink()

    @api.depends("attribute_id")
    def _compute_display_name(self):
        for value in self:
            value.display_name = f"{value.attribute_id.name}: {value.name}"

    def _filtered_active(self):
        return self.filtered(lambda ptav: ptav.ptav_active)

    def _without_no_variant_attributes(self):
        return self.filtered(
            lambda ptav: ptav.attribute_id.create_variant != "no_variant"
        )

    def _ids2str(self):
        return ",".join([str(i) for i in sorted(self.ids)])

    def _get_combination_name(self):
        ptavs = self._without_no_variant_attributes().with_prefetch(self._prefetch_ids)
        ptavs = ptavs._filter_single_value_lines().with_prefetch(self._prefetch_ids)
        return ", ".join([ptav.name for ptav in ptavs])

    def _filter_single_value_lines(self):
        only_active = all(ptav.ptav_active for ptav in self)
        return self.filtered(
            lambda ptav: not ptav._is_from_single_value_line(only_active)
        )

    def _is_from_single_value_line(self, only_active=True):
        self.check_singleton()
        all_values = self.attribute_line_id.product_template_value_ids
        if only_active:
            all_values = all_values._filtered_active()
        return len(all_values) == 1
