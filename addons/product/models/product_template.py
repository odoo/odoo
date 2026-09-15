import itertools
import logging
from collections import defaultdict

from odoo import Command, _, api, fields, models, tools
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.sql import SQL
from odoo.tools.image import is_image_size_above
from odoo.tools.misc import unique

_logger = logging.getLogger(__name__)
PRICE_CONTEXT_KEYS = ["pricelist", "quantity", "uom", "date"]

# the four fields product.template mirrors from its single variant
MANUFACTURER_FIELDS = (
    "manufacturer_id",
    "manufacturer_pname",
    "manufacturer_pref",
    "manufacturer_purl",
)


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.image",
        "mixin.product.price",
        "mixin.favorite",
        "mixin.user.favorite",
    ]
    _description = "Product"
    _order = "is_favorite desc, name"
    _check_company_auto = True
    _check_company_domain = models.check_company_domain_parent_of

    company_id = fields.Many2one(
        comodel_name="res.company",
        index=True,
    )
    currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_currency_id",
    )
    cost_currency_id = fields.Many2one(
        comodel_name="res.currency",
        compute="_compute_cost_currency_id",
    )
    categ_id = fields.Many2one(
        comodel_name="product.category",
        string="Product Category",
        index=True,
        group_expand="_read_group_categ_id",
        check_company=True,
        tracking=True,
    )

    name = fields.Char(
        translate=True,
        index="trigram",
        required=True,
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the product without removing it.",
    )
    sequence = fields.Integer(
        default=1,
        help="Gives the sequence order when displaying a product list",
    )
    color = fields.Integer(string="Color Index")
    is_product_variant = fields.Boolean(
        string="Is a product variant",
        compute="_compute_is_product_variant",
    )
    type = fields.Selection(
        selection=[
            ("consu", "Goods"),
            ("service", "Service"),
            ("combo", "Combo"),
        ],
        string="Product Type",
        default="consu",
        required=True,
        help="Goods are tangible materials and merchandise you provide.\n"
        "A service is a non-material product you provide.",
    )
    service_tracking = fields.Selection(
        selection=[
            ("no", "Nothing"),
        ],
        string="Create on Order",
        compute="_compute_service_tracking",
        default="no",
        store=True,
        readonly=False,
        required=True,
    )

    description = fields.Html(translate=True)
    description_purchase = fields.Text(
        string="Purchase Description",
        translate=True,
    )
    description_sale = fields.Text(
        string="Sales Description",
        translate=True,
        help="A description of the Product that you want to communicate to your customers. "
        "This description will be copied to every Sales Order, Delivery Order and Customer Invoice/Credit Note",
    )

    uom_id = fields.Many2one(
        comodel_name="uom.uom",
        string="Unit",
        default=lambda self: self._default_uom_id(),
        required=True,
        tracking=True,
        help="Default unit of measure used for all stock operations.",
    )
    uom_name = fields.Char(
        related="uom_id.name",
        string="Unit Name",
        readonly=True,
    )
    uom_ids = fields.Many2many(
        comodel_name="uom.uom",
        string="Packagings",
        domain="[('id', '!=', uom_id)]",
        help="Additional packagings for this product which can be used for sales.\n"
        "They must measure the same thing as the product's unit (a box of 6, a"
        " pallet, ...), so that a quantity or a price can be converted between them.",
    )

    combo_ids = fields.Many2many(
        comodel_name="product.combo",
        string="Combo Choices",
        check_company=True,
    )

    seller_ids = fields.One2many(
        comodel_name="product.supplierinfo",
        inverse_name="product_tmpl_id",
        string="Vendors",
        depends_context=("company",),
        domain=lambda self: [("company_id", "in", (False, self.env.company.id))],
    )
    variant_seller_ids = fields.One2many(
        comodel_name="product.supplierinfo",
        inverse_name="product_tmpl_id",
    )

    list_price = fields.Float(
        string="Sales Price",
        min_display_digits="Product Price",
        default=1.0,
        tracking=True,
        help="Price at which the product is sold to customers.",
    )
    standard_price = fields.Float(
        string="Cost",
        min_display_digits="Product Price",
        compute="_compute_standard_price",
        inverse="_inverse_standard_price",
        search="_search_standard_price",
        groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""",
    )

    volume = fields.Float(
        digits="Volume",
        compute="_compute_volume",
        inverse="_inverse_volume",
        store=True,
    )
    volume_uom_name = fields.Char(
        string="Volume unit of measure label",
        compute="_compute_volume_uom_name",
    )
    weight = fields.Float(
        digits="Stock Weight",
        compute="_compute_weight",
        inverse="_inverse_weight",
        store=True,
    )
    weight_uom_name = fields.Char(
        string="Weight unit of measure label",
        compute="_compute_weight_uom_name",
    )

    attribute_line_ids = fields.One2many(
        comodel_name="product.template.attribute.line",
        inverse_name="product_tmpl_id",
        string="Product Attributes",
        copy=True,
    )

    valid_product_template_attribute_line_ids = fields.Many2many(
        comodel_name="product.template.attribute.line",
        string="Valid Product Attribute Lines",
        compute="_compute_valid_product_template_attribute_line_ids",
    )

    import_attribute_values = fields.Char(
        string="Product Values",
        compute="_compute_import_attribute_values",
        inverse="_inverse_import_attribute_values",
        store=False,
        copy=False,
    )

    product_variant_ids = fields.One2many(
        comodel_name="product.product",
        inverse_name="product_tmpl_id",
        string="Products",
        required=True,
    )
    product_variant_id = fields.Many2one(
        comodel_name="product.product",
        string="Product",
        compute="_compute_product_variant_id",
    )
    product_variant_count = fields.Count(
        count_of="product_variant_ids",
        string="# Product Variants",
    )

    barcode = fields.Char(
        compute="_compute_barcode",
        inverse="_inverse_barcode",
        search="_search_barcode",
    )
    default_code = fields.Char(
        string="Internal Reference",
        compute="_compute_default_code",
        inverse="_inverse_default_code",
        store=True,
    )
    # The four manufacturer fields, their strings and the two hook names below
    # are OCA product-attribute's design (AGPL-3; see the note in
    # product_product.py); the bodies are this fork's.
    manufacturer_id = fields.Many2one(
        comodel_name="res.partner",
        compute="_compute_manufacturer_info",
        inverse="_inverse_manufacturer_info",
        store=True,
    )
    manufacturer_pname = fields.Char(
        string="Manufacturer Product Name",
        compute="_compute_manufacturer_info",
        inverse="_inverse_manufacturer_info",
        store=True,
    )
    manufacturer_pref = fields.Char(
        string="Manufacturer Product Code",
        compute="_compute_manufacturer_info",
        inverse="_inverse_manufacturer_info",
        store=True,
    )
    manufacturer_purl = fields.Char(
        string="Manufacturer Product URL",
        compute="_compute_manufacturer_info",
        inverse="_inverse_manufacturer_info",
        store=True,
    )

    pricelist_rule_ids = fields.One2many(
        comodel_name="product.pricelist.item",
        inverse_name="product_tmpl_id",
        string="Pricelist Rules",
        domain=lambda self: self._domain_pricelist_rule_ids(),
    )

    can_image_1024_be_zoomed = fields.Boolean(
        string="Can Image 1024 be zoomed",
        compute="_compute_can_image_1024_be_zoomed",
        store=True,
    )
    has_configurable_attributes = fields.Boolean(
        string="Is a configurable product",
        compute="_compute_has_configurable_attributes",
        store=True,
    )
    sale_ok = fields.Boolean(
        string="Sales",
        default=True,
    )
    purchase_ok = fields.Boolean(
        string="Purchase",
        compute="_compute_purchase_ok",
        default=True,
        store=True,
        readonly=False,
    )
    is_dynamically_created = fields.Boolean(compute="_compute_is_dynamically_created")

    product_tooltip = fields.Char(compute="_compute_product_tooltip")
    product_tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_tag_product_template_rel",
        string="Tags",
    )
    product_properties = fields.Properties(
        definition="categ_id.product_properties_definition",
        string="Properties",
        copy=True,
    )

    _is_favorite_index = models.Index("(is_favorite) WHERE is_favorite IS TRUE")

    @api.constrains("type", "combo_ids")
    def _check_combo_ids_not_empty(self):
        for template in self:
            if template.type == "combo" and not template.combo_ids:
                raise ValidationError(
                    _("A combo product must contain at least 1 combo choice.")
                )

    @api.constrains("type", "combo_ids", "sale_ok")
    def _check_sale_combo_ids(self):
        for template in self:
            if (
                template.type == "combo"
                and template.sale_ok
                and any(
                    not product.sale_ok
                    for product in template.combo_ids.combo_item_ids.product_id
                )
            ):
                raise ValidationError(
                    _("A sellable combo product can only contain sellable products.")
                )

    @api.constrains("company_id")
    def _check_barcode_uniqueness(self):
        self.product_variant_ids._check_barcode_uniqueness()

    @api.constrains("uom_id", "uom_ids")
    def _check_uom_ids_are_convertible(self):
        for template in self:
            if not template.uom_id:
                continue
            incompatible = template.uom_ids.filtered(
                lambda uom, template=template: (
                    not uom._has_common_reference(template.uom_id)
                )
            )
            if incompatible:
                raise ValidationError(
                    _(
                        "The packaging %(packagings)s cannot be used for"
                        " %(product)s: they do not measure the same thing as its"
                        " unit %(unit)s, so no quantity or price could be"
                        " converted between them.",
                        packagings=", ".join(incompatible.mapped("display_name")),
                        product=template.display_name,
                        unit=template.uom_id.display_name,
                    )
                )

    @api.model_create_multi
    def create(self, vals_list):
        templates = super().create(vals_list)
        if self.env.context.get("create_product_product", True):
            templates._create_variant_ids()

        for template, vals in zip(templates, vals_list, strict=True):
            related_vals = {}
            for field_name in self._get_related_fields_variant_template():
                if vals.get(field_name) and not template[field_name]:
                    related_vals[field_name] = vals[field_name]
            if related_vals:
                template.write(related_vals)

        return templates

    def write(self, vals):
        if "uom_id" in vals:
            products = (
                self.filtered(lambda template: template.uom_id.id != vals["uom_id"])
                .with_context(active_test=False)
                .product_variant_ids
            )
            products.with_context(skip_uom_conversion=True)._update_uom(vals["uom_id"])
        res = super().write(vals)
        if self.env.context.get("create_product_product", True):
            if "attribute_line_ids" in vals:
                self._create_variant_ids()
            elif vals.get("active"):
                self.filtered(lambda t: not t.product_variant_ids)._create_variant_ids()
        if "active" in vals and not vals.get("active"):
            self.with_context(active_test=False).product_variant_ids.write(
                {"active": False}
            )
        if "image_1920" in vals:
            self.with_context(
                active_test=False
            ).product_variant_ids.invalidate_recordset(
                [
                    "image_1920",
                    "image_1024",
                    "image_512",
                    "image_256",
                    "image_128",
                    "can_image_1024_be_zoomed",
                ]
            )
        if "type" in vals and vals["type"] != "combo":
            self.filtered(lambda t: t.combo_ids).combo_ids = False
        return res

    def copy(self, default=None):
        res = super().copy(default=default)
        for template, copied_template in zip(
            self.browse(unique(self._ids)), res, strict=True
        ):
            for ptal, copied_ptal in zip(
                template.attribute_line_ids,
                copied_template.attribute_line_ids,
                strict=False,
            ):
                copied_ptav_by_pav = {
                    copied_ptav.product_attribute_value_id: copied_ptav
                    for copied_ptav in copied_ptal.product_template_value_ids
                }
                for ptav in ptal.product_template_value_ids:
                    if not ptav.price_extra:
                        continue
                    copied_ptav = copied_ptav_by_pav.get(
                        ptav.product_attribute_value_id
                    )
                    if copied_ptav and ptav.attribute_id == copied_ptav.attribute_id:
                        copied_ptav.price_extra = ptav.price_extra
        return res

    def copy_data(self, default=None):
        default = dict(default or {})
        vals_list = super().copy_data(default=default)
        if "name" not in default:
            for template, vals in zip(self, vals_list, strict=True):
                if vals is None:
                    continue
                vals["name"] = _("%s (copy)", template.name)
        return vals_list

    def copy_translations(self, new, excluded=()):
        super().copy_translations(new, excluded=(*excluded, "name"))
        self._copy_translations_of_renamed_field(
            new, "name", lambda record, term: record.env._("%s (copy)", term)
        )

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        if ("uom_id" in fields and not res.get("uom_id")) or self.env.context.get(
            "default_uom_id"
        ) is False:
            res["uom_id"] = self._default_uom_id()
        return res

    @tools.ormcache()
    def _default_uom_id(self):
        return self.env.ref("uom.product_uom_unit").id

    def _read_group_categ_id(self, categories, domain):
        category_ids = self.env.context.get("default_categ_id")
        if not category_ids and self.env.context.get("group_expand"):
            category_ids = categories.sudo()._search([], order=categories._order)
        return categories.browse(category_ids)

    def _compute_is_product_variant(self):
        self.is_product_variant = False

    def _compute_purchase_ok(self):
        pass

    @api.depends("type")
    def _compute_service_tracking(self):
        self.filtered(lambda product: product.type != "service").service_tracking = "no"

    @api.depends("image_1920", "image_1024")
    def _compute_can_image_1024_be_zoomed(self):
        for template in self.with_context(bin_size=False):
            template.can_image_1024_be_zoomed = (
                template.image_1920
                and is_image_size_above(template.image_1920, template.image_1024)
            )

    @api.depends(
        "attribute_line_ids",
        "attribute_line_ids.value_ids",
        "attribute_line_ids.attribute_id.create_variant",
        "attribute_line_ids.attribute_id.display_type",
        "attribute_line_ids.value_ids.is_custom",
    )
    def _compute_has_configurable_attributes(self):
        for product in self:
            product.has_configurable_attributes = (
                product.has_dynamic_attributes()
                or any(ptal._is_configurable() for ptal in product.attribute_line_ids)
            )

    @api.depends("attribute_line_ids.attribute_id")
    def _compute_is_dynamically_created(self):
        for template in self:
            template.is_dynamically_created = any(
                line.attribute_id.create_variant == "dynamic"
                for line in template.attribute_line_ids
            )

    @api.depends("product_variant_ids")
    def _compute_product_variant_id(self):
        for p in self:
            p.product_variant_id = p.product_variant_ids[:1].id

    @api.depends("company_id")
    def _compute_currency_id(self):
        main_company = self.env["res.company"]._get_main_company()
        for template in self:
            template.currency_id = (
                template.company_id.sudo().currency_id.id or main_company.currency_id.id
            )

    @api.depends_context("company")
    @api.depends("company_id")
    def _compute_cost_currency_id(self):
        env_currency_id = self.env.company.currency_id.id
        for template in self:
            template.cost_currency_id = (
                template.company_id.sudo().currency_id.id or env_currency_id
            )

    @api.depends_context("company")
    @api.depends("product_variant_ids.standard_price")
    def _compute_standard_price(self):
        self._compute_template_field_from_variant_field("standard_price")

    @api.depends("product_variant_ids.volume")
    def _compute_volume(self):
        self._compute_template_field_from_variant_field("volume")

    @api.depends("product_variant_ids.weight")
    def _compute_weight(self):
        self._compute_template_field_from_variant_field("weight")

    @api.depends("product_variant_ids.barcode")
    def _compute_barcode(self):
        self._compute_template_field_from_variant_field("barcode")

    @api.depends("type")
    def _compute_weight_uom_name(self):
        self.weight_uom_name = self._get_weight_uom_name_from_ir_config_parameter()

    @api.depends("type")
    def _compute_volume_uom_name(self):
        self.volume_uom_name = self._get_volume_uom_name_from_ir_config_parameter()

    @api.depends("product_variant_ids.default_code")
    def _compute_default_code(self):
        self._compute_template_field_from_variant_field("default_code")

    @api.depends(
        "product_variant_ids",
        "product_variant_ids.manufacturer_id",
        "product_variant_ids.manufacturer_pname",
        "product_variant_ids.manufacturer_pref",
        "product_variant_ids.manufacturer_purl",
    )
    def _compute_manufacturer_info(self):
        for fname in MANUFACTURER_FIELDS:
            self._compute_template_field_from_variant_field(fname)

    @api.depends("type")
    def _compute_product_tooltip(self):
        for template in self:
            template.product_tooltip = template._prepare_tooltip()

    def _compute_import_attribute_values(self):
        self.import_attribute_values = ""

    @api.depends("name", "default_code")
    @api.depends_context("formatted_display_name", "display_default_code")
    def _compute_display_name(self):
        display_default_code = self.env.context.get("display_default_code", True)
        for template in self:
            if not template.name:
                template.display_name = False
            elif not (display_default_code and template.default_code):
                template.display_name = template.name
            elif self.env.context.get("formatted_display_name"):
                code_prefix = f"\t--{template.default_code}--"
                template.display_name = f"{template.name}{code_prefix}"
            else:
                code_prefix = f"[{template.default_code}] "
                template.display_name = f"{code_prefix}{template.name}"

    @api.depends("attribute_line_ids.value_ids")
    def _compute_valid_product_template_attribute_line_ids(self):
        for record in self:
            record.valid_product_template_attribute_line_ids = (
                record.attribute_line_ids.filtered(lambda ptal: ptal.value_ids)
            )

    def _set_product_variant_field(self, fname):
        for template in self:
            count = len(template.product_variant_ids)
            if count == 1:
                template.product_variant_ids[fname] = template[fname]
            elif count == 0:
                archived_variants = template.with_context(
                    active_test=False
                ).product_variant_ids
                if len(archived_variants) == 1:
                    archived_variants[fname] = template[fname]

    def _inverse_standard_price(self):
        self._set_product_variant_field("standard_price")

    def _inverse_volume(self):
        self._set_product_variant_field("volume")

    def _inverse_weight(self):
        self._set_product_variant_field("weight")

    def _inverse_barcode(self):
        self._set_product_variant_field("barcode")

    def _inverse_default_code(self):
        self._set_product_variant_field("default_code")

    def _inverse_manufacturer_info(self):
        for fname in MANUFACTURER_FIELDS:
            self._set_product_variant_field(fname)

    def _inverse_import_attribute_values(self):
        raise UserError(_("This field can only be used to import products."))

    def _search_standard_price(self, operator, value):
        return [("product_variant_ids.standard_price", operator, value)]

    def _search_barcode(self, operator, value):
        subquery = self.with_context(active_test=False)._search(
            [
                ("product_variant_ids.barcode", operator, value),
            ]
        )
        return [("id", "in", subquery)]

    @api.model
    def _search_display_name(self, operator, value):
        domain = super()._search_display_name(operator, value)
        if self.env.context.get("search_product_product", bool(value)):
            if operator in Domain.NEGATIVE_OPERATORS:
                domain = Domain.AND(
                    [domain, [("product_variant_ids", operator, value)]],
                )
            else:
                query = SQL(
                    """((%s) UNION ALL (%s))""",
                    self._search(domain).select(),
                    self._search([("product_variant_ids", operator, value)]).select(),
                )
                domain = [("id", "in", query)]
        return domain

    @api.onchange("type")
    def _onchange_type(self):
        if self.type == "combo":
            if self.attribute_line_ids:
                raise UserError(_("Combo products can't have attributes."))
            combo_items = (
                self.env["product.combo.item"]
                .sudo()
                .search([("product_id", "in", self.product_variant_ids.ids)])
            )
            if combo_items:
                raise UserError(
                    _(
                        'This product is part of a combo, so its type can\'t be changed to "combo".'
                    )
                )
            self.purchase_ok = False
        return {}

    @api.onchange("uom_id")
    def _onchange_uom_id(self):
        if (
            self._origin.uom_id == self.uom_id
            or not self.with_context(
                active_test=False
            ).product_variant_ids._is_uom_change_warning_required()
        ):
            return None
        message = _(
            "Changing the unit of measure for your product will apply a conversion 1 %(old_uom_name)s = 1 %(new_uom_name)s.\n"
            "All existing records (Sales orders, Purchase orders, etc.) using this product will be updated by replacing the unit name.",
            old_uom_name=self._origin.uom_id.display_name,
            new_uom_name=self.uom_id.display_name,
        )
        return {
            "warning": {
                "title": _("What to expect ?"),
                "message": message,
            }
        }

    @api.onchange("default_code")
    def _onchange_default_code(self):
        if not self.default_code:
            return None

        domain = [("default_code", "=", self.default_code)]
        if self.id.origin:
            domain.append(("id", "!=", self.id.origin))

        if self.env["product.template"].search_count(domain, limit=1):
            return {
                "warning": {
                    "title": _("Note:"),
                    "message": _(
                        "The Internal Reference '%s' already exists.", self.default_code
                    ),
                }
            }
        return None

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        self_obj = self
        if "search_product_product" not in self.env.context and any(
            condition.field_expr == "id"
            for condition in Domain(domain or Domain.TRUE).iter_conditions()
        ):
            self_obj = self_obj.with_context(search_product_product=False)
        return super(ProductTemplate, self_obj).name_search(
            name,
            domain,
            operator,
            limit,
        )

    def action_view_label_layout(self):
        if any(product_tmpl.type == "service" for product_tmpl in self):
            raise ValidationError(
                _("Labels cannot be printed for products of service type")
            )
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "product.action_view_label_layout"
        )
        action["context"] = {"default_product_tmpl_ids": self.ids}
        return action

    def action_open_packaging_barcodes(self):
        # Every packaging barcode of this product, across all of its units.  The
        # uom.uom stat button only ever scopes by unit, so this is the one
        # product-scoped view of them.
        self.check_singleton()
        variants = self.product_variant_ids
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Packaging Barcodes"),
            "res_model": "product.uom",
            "view_mode": "list",
            "view_id": self.env.ref("product.product_uom_list_view").id,
            "domain": [("product_id", "in", variants.ids)],
            "context": {
                "default_product_id": variants[:1].id,
                "product_ids": variants.ids,
                "show_variant_name": len(variants) > 1,
            },
        }

    def _cartesian_product(
        self, product_template_attribute_values_per_line, parent_combination
    ):
        if not product_template_attribute_values_per_line:
            return

        product_template_attribute_values_per_line = [
            ptav for ptav in product_template_attribute_values_per_line if len(ptav)
        ]
        if not product_template_attribute_values_per_line:
            yield self.env["product.template.attribute.value"]
            return

        all_exclusions = {
            self.env["product.template.attribute.value"].browse(k): self.env[
                "product.template.attribute.value"
            ].browse(v)
            for k, v in self._get_own_attribute_exclusions().items()
        }
        current_exclusions = defaultdict(int)
        for excluded_ids in self._get_parent_attribute_exclusions(
            parent_combination
        ).values():
            for exclusion in excluded_ids:
                current_exclusions[
                    self.env["product.template.attribute.value"].browse(exclusion)
                ] += 1
        partial_combination = self.env["product.template.attribute.value"]

        value_index_per_line = [-1] * len(product_template_attribute_values_per_line)
        line_index = 0

        while True:
            current_line_values = product_template_attribute_values_per_line[line_index]
            current_ptav_index = value_index_per_line[line_index]

            if current_ptav_index >= 0:
                current_ptav = current_line_values[current_ptav_index]
                for ptav_to_include_back in all_exclusions[current_ptav]:
                    current_exclusions[ptav_to_include_back] -= 1
                partial_combination -= current_ptav

            if current_ptav_index < len(current_line_values) - 1:
                value_index_per_line[line_index] += 1
                current_line_values = product_template_attribute_values_per_line[
                    line_index
                ]
                current_ptav_index = value_index_per_line[line_index]
                current_ptav = current_line_values[current_ptav_index]
            elif line_index != 0:
                value_index_per_line[line_index] = -1
                line_index -= 1
                continue
            else:
                break

            for ptav_to_exclude in all_exclusions[current_ptav]:
                current_exclusions[ptav_to_exclude] += 1
            partial_combination += current_ptav

            if current_exclusions[current_ptav] or any(
                intersection in partial_combination
                for intersection in all_exclusions[current_ptav]
            ):
                continue

            if line_index == len(product_template_attribute_values_per_line) - 1:
                yield partial_combination
            else:
                line_index += 1

    @api.model
    def _complete_inverse_exclusions(self, exclusions):
        result = {key: list(value) for key, value in exclusions.items()}
        for key, value in exclusions.items():
            for exclusion in value:
                inverse = result.setdefault(exclusion, [])
                if key not in inverse:
                    inverse.append(key)

        return result

    def _compute_template_field_from_variant_field(self, fname, default=False):
        for template in self:
            variant_count = len(template.product_variant_ids)
            if variant_count == 1:
                template[fname] = template.product_variant_ids[fname]
            elif variant_count == 0 and self.env.context.get("active_test", True):
                template_ctx = template.with_context(active_test=False)
                template_ctx._compute_template_field_from_variant_field(
                    fname, default=default
                )
            else:
                template[fname] = default

    def _get_price_base(self, price_type):
        price = super()._get_price_base(price_type)
        if price_type == "standard_price" and not price and self.product_variant_ids:
            price = self.product_variant_ids[0].standard_price
        return price

    def _create_first_product_variant(self, log_warning=False):
        return self._create_product_variant(
            self._get_first_possible_combination(), log_warning
        )

    def _create_product_variant(self, combination, log_warning=False):
        self.check_singleton()

        Product = self.env["product.product"]

        product_variant = self._get_variant_for_combination(combination)
        if product_variant:
            if (
                not product_variant.active
                and self.has_dynamic_attributes()
                and self._is_combination_possible(combination)
            ):
                product_variant.active = True
            return product_variant

        if not self.has_dynamic_attributes():
            if log_warning:
                _logger.warning(
                    "The user #%s tried to create a variant for the non-dynamic product %s.",
                    self.env.user.id,
                    self.id,
                )
            return Product

        if not self._is_combination_possible(combination):
            if log_warning:
                _logger.warning(
                    "The user #%s tried to create an invalid variant for the product %s.",
                    self.env.user.id,
                    self.id,
                )
            return Product

        return Product.sudo().create(
            {
                "product_tmpl_id": self.id,
                "product_template_attribute_value_ids": [
                    (6, 0, combination._without_no_variant_attributes().ids)
                ],
            }
        )

    def _create_variant_ids(self):
        if not self:
            return None
        self.env.flush_all()
        Product = self.env["product.product"]

        variants_to_create = []
        variants_to_activate = Product
        variants_to_unlink = Product

        raw_variant_limit = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("product.dynamic_variant_limit", 1000)
        )
        try:
            variant_limit = int(raw_variant_limit)
        except ValueError, TypeError:
            _logger.warning(
                "Ignoring invalid product.dynamic_variant_limit %r, using %s.",
                raw_variant_limit,
                1000,
            )
            variant_limit = 1000

        for tmpl_id in self:
            lines_without_no_variants = tmpl_id.valid_product_template_attribute_line_ids._without_no_variant_attributes()

            all_variants = tmpl_id.with_context(
                active_test=False
            ).product_variant_ids.sorted(lambda p: (p.active, -p.id))

            current_variants_to_create = []
            current_variants_to_activate = Product

            single_value_lines = lines_without_no_variants.filtered(
                lambda ptal: (
                    len(ptal.product_template_value_ids._filtered_active()) == 1
                )
            )
            if single_value_lines:
                for variant in all_variants:
                    combination = (
                        variant.product_template_attribute_value_ids
                        | single_value_lines.product_template_value_ids._filtered_active()
                    )
                    if (
                        len(combination) == len(lines_without_no_variants)
                        and combination.attribute_line_id == lines_without_no_variants
                        and variant.product_template_attribute_value_ids != combination
                    ):
                        variant.product_template_attribute_value_ids = combination

            existing_variants = {
                variant.product_template_attribute_value_ids: variant
                for variant in all_variants
            }

            if not tmpl_id.has_dynamic_attributes():
                all_combinations = itertools.product(
                    *[
                        ptal.product_template_value_ids._filtered_active()
                        for ptal in lines_without_no_variants
                    ]
                )
                for combination in tmpl_id._filter_combinations_impossible_by_config(
                    all_combinations,
                    ignore_no_variant=True,
                ):
                    if combination in existing_variants:
                        current_variants_to_activate += existing_variants[combination]
                    else:
                        current_variants_to_create.append(
                            tmpl_id._prepare_variant_values(combination)
                        )
                        if len(current_variants_to_create) > variant_limit:
                            raise UserError(
                                _(
                                    "The number of variants to generate is above allowed limit. "
                                    "You should either not generate variants for each combination or generate them on demand from the sales order. "
                                    "To do so, open the form view of attributes and change the mode of *Create Variants*."
                                )
                            )
                variants_to_create += current_variants_to_create
                variants_to_activate += current_variants_to_activate

            elif existing_variants:
                variants_combinations = [
                    variant.product_template_attribute_value_ids
                    for variant in existing_variants.values()
                ]
                current_variants_to_activate += Product.concat(
                    *[
                        existing_variants[possible_combination]
                        for possible_combination in tmpl_id._filter_combinations_impossible_by_config(
                            variants_combinations, ignore_no_variant=True
                        )
                    ]
                )
                variants_to_activate += current_variants_to_activate

            variants_to_unlink += all_variants - current_variants_to_activate

        if variants_to_activate:
            variants_to_activate.filtered(lambda v: v.product_tmpl_id.active).write(
                {"active": True}
            )
        if variants_to_create:
            Product.create(variants_to_create)
        if variants_to_unlink:
            variants_to_unlink._unlink_or_archive()
            if self.exists() != self:
                raise UserError(
                    _(
                        "This configuration of product attributes, values, and exclusions would lead to no possible variant. Please archive or delete your product directly if intended."
                    )
                )
            combo_items_to_unlink = self.env["product.combo.item"].search(
                [("product_id", "in", variants_to_unlink.ids)]
            )
            combo_items_to_unlink.unlink()

        self.env.flush_all()
        self.env.invalidate_all()
        return True

    def _filter_combinations_impossible_by_config(
        self, combination_tuples, ignore_no_variant=False
    ):
        self.check_singleton()
        attribute_lines = self.valid_product_template_attribute_line_ids
        attribute_lines_active_values = (
            attribute_lines.product_template_value_ids._filtered_active()
        )
        if ignore_no_variant:
            attribute_lines = attribute_lines._without_no_variant_attributes()
        attribute_lines_without_multi = attribute_lines.filtered(
            lambda l: l.attribute_id.display_type != "multi"
        )
        exclusions = self._get_own_attribute_exclusions()
        for combination_tuple in combination_tuples:
            combination = self.env["product.template.attribute.value"].concat(
                *combination_tuple
            )
            combination_without_multi = combination.filtered(
                lambda l: l.attribute_line_id.attribute_id.display_type != "multi"
            )
            if len(combination_without_multi) != len(attribute_lines_without_multi):
                continue
            if (
                attribute_lines_without_multi
                != combination_without_multi.attribute_line_id
            ):
                continue
            if not (attribute_lines_active_values >= combination):
                continue
            if exclusions:
                combination_ids = set(combination.ids)
                combination_excluded_ids = set(
                    itertools.chain(
                        *[exclusions.get(ptav_id, ()) for ptav_id in combination.ids]
                    )
                )
                if combination_ids & combination_excluded_ids:
                    continue
            yield combination

    def _get_archived_combinations(self, combination_ids=None):
        self.check_singleton()
        archived_products = self.with_context(
            active_test=False
        ).product_variant_ids.filtered(lambda l: not l.active)
        active_combinations = {
            tuple(product.product_template_attribute_value_ids.ids)
            for product in self.product_variant_ids
        }
        return list(
            {
                tuple(product.product_template_attribute_value_ids.ids)
                for product in archived_products
                if product.product_template_attribute_value_ids
                and all(
                    ptav.ptav_active or (combination_ids and ptav.id in combination_ids)
                    for ptav in product.product_template_attribute_value_ids
                )
            }
            - active_combinations
        )

    def _get_attribute_exclusions(
        self, parent_combination=None, parent_name=None, combination_ids=None
    ):
        self.check_singleton()
        parent_combination = (
            parent_combination or self.env["product.template.attribute.value"]
        )
        return {
            "exclusions": self._complete_inverse_exclusions(
                self._get_own_attribute_exclusions(combination_ids=combination_ids)
            ),
            "archived_combinations": self._get_archived_combinations(
                combination_ids=combination_ids
            ),
            "parent_exclusions": self._get_parent_attribute_exclusions(
                parent_combination
            ),
            "parent_combination": parent_combination.ids,
            "parent_product_name": parent_name,
            "mapped_attribute_names": self._get_mapped_attribute_names(
                parent_combination
            ),
        }

    def _get_attributes_extra_price(self):
        self.check_singleton()

        return sum(self.env.context.get("current_attributes_price_extra", []))

    def _prepare_product_price_context(self, combination):
        self.check_singleton()
        res = {}

        current_attributes_price_extra = [
            ptav.price_extra
            for ptav in combination.filtered(
                lambda ptav: ptav.price_extra and ptav.product_tmpl_id == self
            )
        ]
        if current_attributes_price_extra:
            res["current_attributes_price_extra"] = tuple(
                current_attributes_price_extra
            )

        return res

    def _get_possible_variants(self, parent_combination=None):
        self.check_singleton()
        return self.product_variant_ids.filtered(
            lambda p: p._is_variant_possible(parent_combination)
        )

    def _get_own_attribute_exclusions(self, combination_ids=None):
        self.check_singleton()
        combination_ids = frozenset(combination_ids or ())
        own_values = (
            self.valid_product_template_attribute_line_ids.product_template_value_ids
        )
        result = {}
        for ptav in own_values:
            if not (ptav.ptav_active or ptav.id in combination_ids):
                continue
            own_exclusions = ptav.exclude_for.filtered(
                lambda exclusion, template=self: exclusion.product_tmpl_id == template
            )
            result[ptav.id] = own_exclusions.value_ids.filtered("ptav_active").ids
        return result

    def _get_parent_attribute_exclusions(self, parent_combination):
        self.check_singleton()
        if not parent_combination:
            return {}

        result = {}
        for product_attribute_value in parent_combination:
            for filter_line in product_attribute_value.exclude_for.filtered(
                lambda filter_line: filter_line.product_tmpl_id == self
            ):
                if filter_line.value_ids:
                    result[product_attribute_value.id] = filter_line.value_ids.ids
                else:
                    result[product_attribute_value.id] = (
                        filter_line.product_tmpl_id.mapped(
                            "attribute_line_ids.product_template_value_ids"
                        ).ids
                    )

        return result

    def _get_mapped_attribute_names(self, parent_combination=None):
        self.check_singleton()
        all_product_attribute_values = (
            self.valid_product_template_attribute_line_ids.product_template_value_ids
        )
        if parent_combination:
            all_product_attribute_values |= parent_combination

        return {
            attribute_value.id: attribute_value.display_name
            for attribute_value in all_product_attribute_values
        }

    def _get_variant_for_combination(self, combination):
        self.check_singleton()
        filtered_combination = combination._without_no_variant_attributes()
        return self.env["product.product"].browse(
            self._get_variant_id_for_combination(filtered_combination)
        )

    @tools.ormcache(
        "self.id", "frozenset(filtered_combination.ids)", cache="product_variants"
    )
    def _get_variant_id_for_combination(self, filtered_combination):
        self.check_singleton()
        domain = Domain("product_tmpl_id", "=", self.id)
        combination_indices_ids = filtered_combination._ids2str()

        if combination_indices_ids:
            domain &= Domain("combination_indices", "=", combination_indices_ids)
        else:
            domain &= Domain("combination_indices", "in", ["", False])

        return (
            self.env["product.product"]
            .sudo()
            .with_context(active_test=False)
            .search(domain, order="active DESC", limit=1)
            .id
        )

    @tools.ormcache("self.id", cache="product_variants")
    def _get_first_possible_variant_id(self):
        self.check_singleton()
        return self._create_first_product_variant().id

    def _get_first_possible_combination(
        self, parent_combination=None, necessary_values=None
    ):
        return next(
            self._get_possible_combinations(parent_combination, necessary_values),
            self.env["product.template.attribute.value"],
        )

    def _get_possible_combinations(
        self, parent_combination=None, necessary_values=None
    ):
        self.check_singleton()

        if not self.active:
            return

        necessary_values = (
            necessary_values or self.env["product.template.attribute.value"]
        )
        necessary_attribute_lines = necessary_values.mapped("attribute_line_id")
        attribute_lines = self.valid_product_template_attribute_line_ids.filtered(
            lambda ptal: ptal not in necessary_attribute_lines
        )

        if not attribute_lines and self._is_combination_possible(
            necessary_values, parent_combination
        ):
            yield necessary_values

        product_template_attribute_values_per_line = []
        for ptal in attribute_lines:
            if ptal.attribute_id.display_type != "multi":
                values_to_add = ptal.product_template_value_ids._filtered_active()
            else:
                values_to_add = self.env["product.template.attribute.value"]
            product_template_attribute_values_per_line.append(values_to_add)

        for partial_combination in self._cartesian_product(
            product_template_attribute_values_per_line, parent_combination
        ):
            combination = partial_combination + necessary_values
            if self._is_combination_possible(combination, parent_combination):
                yield combination

    def _get_closest_possible_combination(self, combination):
        return next(
            self._get_closest_possible_combinations(combination),
            self.env["product.template.attribute.value"],
        )

    def _get_closest_possible_combinations(self, combination):
        while True:
            res = self._get_possible_combinations(necessary_values=combination)
            try:
                yield next(res)
                yield from res
                return
            except StopIteration:
                if not combination:
                    return
                combination = combination[:-1]

    def _get_placeholder_filename(self, field):
        image_fields = ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
        if field in image_fields:
            return self._get_product_placeholder_filename()
        return super()._get_placeholder_filename(field)

    def _get_product_placeholder_filename(self):
        return "product/static/img/placeholder_thumbnail.png"

    def get_single_product_variant(self):
        self.check_singleton()
        if self.product_variant_count == 1 and not self.has_configurable_attributes:
            return {
                "product_id": self.product_variant_id.id,
                "product_name": self.product_variant_id.display_name,
            }
        return {}

    @api.model
    def get_empty_list_help(self, help_message):
        self = self.with_context(
            empty_list_help_document_name=_("product"),
        )
        return super().get_empty_list_help(help_message)

    @api.model
    def get_import_templates(self):
        return [
            {
                "label": _("Import Template for Products"),
                "template": "/product/static/xls/product_product.xls",
            }
        ]

    def get_contextual_price(self, product=None):
        return self._get_contextual_price(product=product)

    def _get_contextual_price(self, product=None):
        self.check_singleton()
        pricelist = self._get_contextual_pricelist()
        quantity = self.env.context.get("quantity", 1.0)
        uom = self.env["uom.uom"].browse(self.env.context.get("uom"))
        date = self.env.context.get("date")
        return pricelist._get_product_price(
            product or self, quantity, uom=uom, date=date
        )

    def _get_contextual_pricelist(self):
        return self.env["product.pricelist"].browse(self.env.context.get("pricelist"))

    def _get_list_price(self, price):
        self.check_singleton()
        return price

    def _get_available_uoms(self):
        self.check_singleton()
        return self.uom_id | self.uom_ids

    @api.model
    def _get_uom_id_from_ir_config_parameter(self, param_key, ref_if_set, ref_default):
        if self.env["ir.config_parameter"].sudo().get_param(param_key) == "1":
            return self.env.ref(ref_if_set)
        return self.env.ref(ref_default)

    @api.model
    def _get_length_uom_id_from_ir_config_parameter(self):
        return self._get_uom_id_from_ir_config_parameter(
            "product.volume_in_cubic_feet",
            "uom.product_uom_foot",
            "uom.product_uom_millimeter",
        )

    @api.model
    def _get_length_uom_name_from_ir_config_parameter(self):
        return self._get_length_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_volume_uom_id_from_ir_config_parameter(self):
        return self._get_uom_id_from_ir_config_parameter(
            "product.volume_in_cubic_feet",
            "uom.product_uom_cubic_foot",
            "uom.product_uom_cubic_meter",
        )

    @api.model
    def _get_volume_uom_name_from_ir_config_parameter(self):
        return self._get_volume_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_weight_uom_name_from_ir_config_parameter(self):
        return self._get_weight_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_weight_uom_id_from_ir_config_parameter(self):
        return self._get_uom_id_from_ir_config_parameter(
            "product.weight_in_lbs", "uom.product_uom_lb", "uom.product_uom_kgm"
        )

    @api.model
    def _get_odometer_uom_id_from_ir_config_parameter(self):
        return self._get_uom_id_from_ir_config_parameter(
            "product.odometer_in_mi",
            "uom.product_uom_mile",
            "uom.product_uom_km",
        )

    @api.model
    def _get_odometer_uom_name_from_ir_config_parameter(self):
        return self._get_odometer_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_area_uom_id_from_ir_config_parameter(self):
        return self._get_uom_id_from_ir_config_parameter(
            "product.area_in_square_ft",
            "uom.product_uom_square_foot",
            "uom.product_uom_square_meter",
        )

    @api.model
    def _get_area_uom_name_from_ir_config_parameter(self):
        return self._get_area_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_power_uom_id_from_ir_config_parameter(self):
        return self._get_uom_id_from_ir_config_parameter(
            "product.power_in_hp",
            "uom.product_uom_hp",
            "uom.product_uom_kw",
        )

    @api.model
    def _get_power_uom_name_from_ir_config_parameter(self):
        return self._get_power_uom_id_from_ir_config_parameter().display_name

    @api.model
    def _get_fuel_efficiency_uom_id_from_ir_config_parameter(self):
        return self._get_uom_id_from_ir_config_parameter(
            "product.fuel_efficiency_in_mpg",
            "uom.product_uom_miles_per_galon",
            "uom.product_uom_km_per_liter",
        )

    @api.model
    def _get_fuel_efficiency_uom_name_from_ir_config_parameter(self):
        return self._get_fuel_efficiency_uom_id_from_ir_config_parameter().display_name

    def _get_related_fields_variant_template(self):
        return [
            "barcode",
            "default_code",
            "standard_price",
            "volume",
            "weight",
            "product_properties",
            *MANUFACTURER_FIELDS,
        ]

    @api.model
    def load(self, fields, data):
        if "import_attribute_values" not in fields:
            return super().load(fields, data)

        column_no = fields.index("import_attribute_values")

        limit = self.env.context.get("_import_limit")
        self = self.with_context(_import_limit=None)

        data_list_products = []
        data_list_templates = []
        rows_products = []
        rows_templates = []
        continuation = self._import_continuation_rows(fields, data)
        to_products = False
        for row, values in enumerate(data):
            if not continuation[row]:
                to_products = bool(values[column_no].strip())
            if to_products:
                data_list_products.append(values)
                rows_products.append(row)
            else:
                values = list(values)
                values.pop(column_no)
                data_list_templates.append(values)
                rows_templates.append(row)

        if data_list_templates:
            template_fields = list(fields)
            template_fields.pop(column_no)
            result = super().load(template_fields, data_list_templates)
            self._restate_import_message_rows(result["messages"], rows_templates)
            if any(message["type"] == "error" for message in result["messages"]):
                return result
        else:
            result = {"ids": [], "messages": [], "nextrow": 0}

        if data_list_products:
            ProductProduct = self.env["product.product"].with_context(
                from_template_import=True
            )
            result_product = ProductProduct.load(fields, data_list_products)
            self._restate_import_message_rows(result_product["messages"], rows_products)
            if any(
                message["type"] == "error" for message in result_product["messages"]
            ):
                return result_product

            product_templates = ProductProduct.browse(
                result_product["ids"]
            ).product_tmpl_id
            result["ids"].extend(product_templates.ids)
            result["messages"].extend(result_product["messages"])

        result["nextrow"] = 0 if limit is None or len(data) < limit else len(data)
        return result

    @api.model
    def _import_continuation_rows(self, fields, data):
        o2m_indexes, other_indexes = [], []
        for index, path in enumerate(fields):
            name = path[0] if isinstance(path, list | tuple) else path.split("/")[0]
            field = self._fields.get(name)
            target = (
                o2m_indexes
                if field is not None and field.type == "one2many"
                else other_indexes
            )
            target.append(index)

        if not o2m_indexes:
            return [False] * len(data)

        return [
            bool(
                index
                and any(row[i] for i in o2m_indexes if i < len(row))
                and not any(row[i] for i in other_indexes if i < len(row))
            )
            for index, row in enumerate(data)
        ]

    @api.model
    def _restate_import_message_rows(self, messages, rows):

        def restate(index):
            if type(index) is not int or not 0 <= index < len(rows):
                return index
            return rows[index]

        for message in messages:
            if isinstance(message.get("rows"), dict):
                message["rows"] = {
                    key: restate(index) for key, index in message["rows"].items()
                }
            if "record" in message:
                message["record"] = restate(message["record"])

    def _prepare_tooltip(self):
        self.check_singleton()
        tooltip = ""
        if self.type == "combo":
            tooltip = _(
                "Combos allow to choose one product amongst a selection of choices per category."
            )
        return tooltip

    def _prepare_variant_values(self, combination):
        self.check_singleton()
        return {
            "product_tmpl_id": self.id,
            "product_template_attribute_value_ids": [Command.set(combination.ids)],
            "active": self.active,
        }

    @api.model
    def _service_tracking_blacklist(self) -> list:
        return []

    def _get_domain_item_ids_base(self):
        return [
            "|",
            ("pricelist_id", "=", False),
            ("pricelist_id.active", "=", True),
        ]

    def _domain_pricelist_rule_ids(self):
        return self._get_domain_item_ids_base()

    def has_dynamic_attributes(self):
        self.check_singleton()
        return any(
            a.create_variant == "dynamic"
            for a in self.valid_product_template_attribute_line_ids.attribute_id
        )

    def _has_multiple_uoms(self) -> bool:
        if self.type == "combo":
            return False
        return (
            self.env["res.groups"]._is_feature_enabled("uom.group_uom")
            and len(self._get_available_uoms()) > 1
        )

    def _is_combination_possible_by_config(self, combination, ignore_no_variant=False):
        self.check_singleton()
        return (
            next(
                self._filter_combinations_impossible_by_config(
                    [combination], ignore_no_variant
                ),
                None,
            )
            is not None
        )

    def _is_combination_possible(
        self, combination, parent_combination=None, ignore_no_variant=False
    ):
        self.check_singleton()

        if not self._is_combination_possible_by_config(combination, ignore_no_variant):
            return False

        variant = self._get_variant_for_combination(combination)

        if self.has_dynamic_attributes():
            if variant and not variant.active:
                return False
        elif not variant or not variant.active:
            return False

        parent_exclusions = self._get_parent_attribute_exclusions(parent_combination)
        if parent_exclusions:
            for exclusions_values in parent_exclusions.values():
                for exclusion in exclusions_values:
                    if exclusion in combination.ids:
                        return False

        return True

    @api.model
    def _demo_configure_variants(self):
        acoustic_bloc_screens = self.env.ref(
            "product.product_template_acoustic_bloc_screens", raise_if_not_found=False
        )
        if acoustic_bloc_screens:
            acoustic_bloc_screens.product_variant_ids[0].default_code = "FURN_6666"
            acoustic_bloc_screens.product_variant_ids[1].default_code = "FURN_6667"
            self.env["ir.model.data"]._update_xmlids(
                [
                    {
                        "xml_id": "product.product_product_25",
                        "record": acoustic_bloc_screens.product_variant_ids[1],
                        "noupdate": True,
                    },
                ],
            )
