import re
from collections import defaultdict

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.fields import Domain
from odoo.libs.sql import SQL
from odoo.tools import OrderedSet, float_compare, groupby
from odoo.tools.image import is_image_size_above
from odoo.tools.misc import unique

from .utils import unlink_where_possible

IMAGE_SIZES = (1920, 1024, 512, 256, 128)


class ProductProduct(models.Model):
    _name = "product.product"
    _description = "Product Variant"
    _inherits = {"product.template": "product_tmpl_id"}
    _inherit = [
        "mixin.mail.thread",
        "mixin.mail.activity",
        "mixin.product.price",
    ]
    _order = "default_code, name, id"
    _search_visibility_fields = ()
    _check_company_domain = models.check_company_domain_parent_of

    product_tmpl_id = fields.Many2one(
        comodel_name="product.template",
        string="Product Template",
        index=True,
        required=True,
        ondelete="cascade",
        bypass_search_access=True,
    )
    is_favorite = fields.Boolean(  # noqa: E8529  index (is_favorite) partial
        related="product_tmpl_id.is_favorite",
        store=True,
        readonly=False,
    )
    # Not stored, unlike its global sibling: the value differs per user, so
    # there is no one column that could hold it.
    is_user_favorite = fields.Boolean(
        related="product_tmpl_id.is_user_favorite",
        readonly=False,
    )
    active = fields.Boolean(
        default=True,
        help="If unchecked, it will allow you to hide the product without removing it.",
    )
    is_product_variant = fields.Boolean(compute="_compute_is_product_variant")
    default_code = fields.Char(
        string="Internal Reference",
        index=True,
    )
    code = fields.Char(
        string="Reference",
        compute="_compute_code",
    )
    barcode = fields.Char(
        index="btree_not_null",
        copy=False,
        help="International Article Number used for product identification.",
    )
    partner_ref = fields.Char(
        string="Customer Ref",
        compute="_compute_partner_ref",
    )
    # Verbatim from OCA product-attribute's product_manufacturer (AGPL-3;
    # OpenERP SA and the Odoo Community Association), which reached this module
    # through agromarin's port of it. They ship under this module's LGPL-3 by
    # the fork owner's decision of 2026-09-09, recorded in the knowledge vault
    # under research/2026-09-09-product-manufacturer-licence-provenance.md
    manufacturer_id = fields.Many2one(comodel_name="res.partner")
    manufacturer_pname = fields.Char(string="Manufacturer Product Name")
    manufacturer_pref = fields.Char(string="Manufacturer Product Code")
    manufacturer_purl = fields.Char(string="Manufacturer Product URL")

    product_uom_ids = fields.One2many(
        comodel_name="product.uom",
        inverse_name="product_id",
        string="Unit Barcode",
    )

    price_extra = fields.Float(
        string="Variant Price Extra",
        min_display_digits="Product Price",
        compute="_compute_price_extra",
        help="This is the sum of the extra price of all attributes",
    )
    lst_price = fields.Float(
        string="Public Price",
        min_display_digits="Product Price",
        compute="_compute_lst_price",
        inverse="_inverse_lst_price",
        help="The sale price is managed from the product template. Click on the 'Configure Variants' button to set the extra attribute prices.",
    )

    standard_price = fields.Float(
        string="Cost",
        min_display_digits="Product Price",
        company_dependent=True,
        groups="base.group_user",
        help="""Value of the product (automatically computed in AVCO).
        Used to value the product when the purchase cost is not known (e.g. inventory adjustment).
        Used to compute margins on sale orders.""",
    )
    volume = fields.Float(digits="Volume")
    weight = fields.Float(digits="Stock Weight")

    product_template_attribute_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        relation="product_variant_combination",
        string="Attribute Values",
        ondelete="restrict",
    )
    product_template_variant_value_ids = fields.Many2many(
        comodel_name="product.template.attribute.value",
        relation="product_variant_combination",
        string="Variant Values",
        readonly=True,
        domain=[("attribute_line_id.value_count", ">", 1)],
        ondelete="restrict",
    )
    import_attribute_values = fields.Char(
        string="Product Values",
        compute="_compute_import_attribute_values",
        inverse="_inverse_import_attribute_values",
        store=False,
        copy=False,
    )
    combination_indices = fields.Char(
        compute="_compute_combination_indices",
        store=True,
        index=True,
    )

    pricelist_rule_ids = fields.One2many(
        comodel_name="product.pricelist.item",
        inverse_name="product_id",
        string="Pricelist Rules",
        compute="_compute_pricelist_rule_ids",
        inverse="_inverse_pricelist_rule_ids",
        readonly=False,
    )

    additional_product_tag_ids = fields.Many2many(
        comodel_name="product.tag",
        relation="product_tag_product_product_rel",
        string="Variant Tags",
        domain="[('id', 'not in', product_tag_ids)]",
    )
    all_product_tag_ids = fields.Many2many(
        comodel_name="product.tag",
        compute="_compute_all_product_tag_ids",
        search="_search_all_product_tag_ids",
    )
    write_date = fields.Datetime(
        compute="_compute_write_date",
        store=True,
    )

    is_in_selected_section_of_order = fields.Boolean(
        search="_search_is_in_selected_section_of_order"
    )

    image_variant_1920 = fields.Image(
        string="Variant Image",
        max_width=1920,
        max_height=1920,
    )

    image_variant_1024 = fields.Image(
        related="image_variant_1920",
        string="Variant Image 1024",
        max_width=1024,
        max_height=1024,
        store=True,
    )
    image_variant_512 = fields.Image(
        related="image_variant_1920",
        string="Variant Image 512",
        max_width=512,
        max_height=512,
        store=True,
    )
    image_variant_256 = fields.Image(
        related="image_variant_1920",
        string="Variant Image 256",
        max_width=256,
        max_height=256,
        store=True,
    )
    image_variant_128 = fields.Image(
        related="image_variant_1920",
        string="Variant Image 128",
        max_width=128,
        max_height=128,
        store=True,
    )
    can_image_variant_1024_be_zoomed = fields.Boolean(
        string="Can Variant Image 1024 be zoomed",
        compute="_compute_can_image_variant_1024_be_zoomed",
        store=True,
    )

    image_1920 = fields.Image(
        string="Image",
        compute="_compute_image_1920",
        inverse="_inverse_image_1920",
    )
    image_1024 = fields.Image(compute="_compute_image_1024")
    image_512 = fields.Image(compute="_compute_image_512")
    image_256 = fields.Image(compute="_compute_image_256")
    image_128 = fields.Image(compute="_compute_image_128")
    can_image_1024_be_zoomed = fields.Boolean(
        string="Can Image 1024 be zoomed",
        compute="_compute_can_image_1024_be_zoomed",
    )

    _is_favorite_index = models.Index("(is_favorite) WHERE is_favorite IS TRUE")
    _combination_unique = models.UniqueIndex(
        "(product_tmpl_id, combination_indices) WHERE active IS TRUE",
    )

    @api.constrains("barcode")
    def _check_barcode_uniqueness(self):
        self_ctx = self.with_context(skip_preprocess_gs1=True)
        for company_id, barcodes_within_company in self_ctx._get_barcodes_by_company():
            self_ctx._check_duplicated_product_barcodes(
                barcodes_within_company,
                company_id,
            )
            self_ctx._check_duplicated_packaging_barcodes(
                barcodes_within_company,
                company_id,
            )

    @api.constrains("company_id")
    def _check_company_id(self):
        combo_items = (
            self.env["product.combo.item"]
            .sudo()
            .search([("product_id", "in", self.ids)])
        )
        combo_items._check_company(fnames=["product_id"])

    @api.constrains("standard_price")
    def _check_standard_price(self):
        for product in self:
            if product.standard_price < 0:
                raise ValidationError(
                    self.env._("The cost of a product can't be negative."),
                )

    @api.model_create_multi
    def create(self, vals_list):
        products = super(
            ProductProduct,
            self.with_context(create_product_product=False),
        ).create(vals_list)
        self.env.registry.clear_cache("product_variants")
        return products.with_env(self.env)

    def write(self, vals):
        # Starring for yourself needs read access, not write, and the record
        # that holds the favorite is the template. Forwarding it here keeps
        # super().write()'s write-access check on the variant off that path.
        if "is_user_favorite" in vals:
            self.product_tmpl_id._update_user_favorite(vals.pop("is_user_favorite"))
            if not vals:
                return True
        res = super().write(vals)
        if "product_template_variant_value_ids" in vals:
            self.invalidate_recordset(["product_template_attribute_value_ids"])
            self.modified(["product_template_attribute_value_ids"])
        if (
            "product_template_attribute_value_ids" in vals
            or "product_template_variant_value_ids" in vals
            or "active" in vals
            or "product_tmpl_id" in vals
        ):
            self.env.registry.clear_cache("product_variants")
        return res

    def copy(self, default=None):

        templates_to_copy = self.product_tmpl_id
        new_templates = templates_to_copy.copy(default=default)
        new_product_list = [
            new_template.product_variant_id
            or new_template._create_first_product_variant()
            for new_template in new_templates
        ]
        return self.env["product.product"].concat(*new_product_list)

    def unlink(self):
        if self.env.context.get("create_product_product") is False:
            res = super().unlink()
            self.env.registry.clear_cache("product_variants")
            return res

        unlink_products_ids = set()
        unlink_templates_ids = set()

        existing_products = self.exists()
        product_ids_by_template_id = {
            template.id: set(ids)
            for template, ids in self.with_context(active_test=False)._read_group(
                domain=[
                    ("product_tmpl_id", "in", existing_products.product_tmpl_id.ids),
                ],
                groupby=["product_tmpl_id"],
                aggregates=["id:array_agg"],
            )
        }
        for product in existing_products.with_context(bin_size=False):
            if product.image_variant_1920 and not product.product_tmpl_id.image_1920:
                product.product_tmpl_id.image_1920 = product.image_variant_1920
            has_other_products = product_ids_by_template_id.get(
                product.product_tmpl_id.id,
                set(),
            ) - {product.id}
            if (
                not has_other_products
                and not product.product_tmpl_id.has_dynamic_attributes()
            ):
                unlink_templates_ids.add(product.product_tmpl_id.id)
            unlink_products_ids.add(product.id)
        unlink_products = self.env["product.product"].browse(unlink_products_ids)
        res = super(ProductProduct, unlink_products).unlink()
        unlink_templates = self.env["product.template"].browse(unlink_templates_ids)
        unlink_templates.unlink()
        self.env.registry.clear_cache("product_variants")
        return res

    @api.depends("product_template_attribute_value_ids")
    def _compute_import_attribute_values(self):
        for product in self:
            product.import_attribute_values = ",".join(
                sorted(
                    f"{ptav.attribute_line_id.attribute_id.name}:{ptav.product_attribute_value_id.name}"
                    for ptav in product.product_template_attribute_value_ids
                )
            )

    def _compute_variant_image(self, size):
        field = "image_%s" % size
        variant_field = "image_variant_%s" % size
        for record in self:
            record[field] = record[variant_field] or record.product_tmpl_id[field]

    @api.depends("image_variant_1920", "product_tmpl_id.image_1920")
    def _compute_image_1920(self):
        self._compute_variant_image(1920)

    @api.depends("image_variant_1024", "product_tmpl_id.image_1024")
    def _compute_image_1024(self):
        self._compute_variant_image(1024)

    @api.depends("image_variant_512", "product_tmpl_id.image_512")
    def _compute_image_512(self):
        self._compute_variant_image(512)

    @api.depends("image_variant_256", "product_tmpl_id.image_256")
    def _compute_image_256(self):
        self._compute_variant_image(256)

    @api.depends("image_variant_128", "product_tmpl_id.image_128")
    def _compute_image_128(self):
        self._compute_variant_image(128)

    @api.depends(
        "image_variant_1920",
        "can_image_variant_1024_be_zoomed",
        "product_tmpl_id.can_image_1024_be_zoomed",
    )
    def _compute_can_image_1024_be_zoomed(self):
        for record in self:
            record.can_image_1024_be_zoomed = (
                record.can_image_variant_1024_be_zoomed
                if record.image_variant_1920
                else record.product_tmpl_id.can_image_1024_be_zoomed
            )

    @api.depends("image_variant_1920", "image_variant_1024")
    def _compute_can_image_variant_1024_be_zoomed(self):
        for record in self.with_context(bin_size=False):
            record.can_image_variant_1024_be_zoomed = (
                record.image_variant_1920
                and is_image_size_above(
                    record.image_variant_1920,
                    record.image_variant_1024,
                )
            )

    @api.depends("product_tmpl_id.pricelist_rule_ids")
    def _compute_pricelist_rule_ids(self):
        for product in self:
            if not product.id:
                product.pricelist_rule_ids = False
                continue
            product.pricelist_rule_ids = (
                product.product_tmpl_id.pricelist_rule_ids.filtered(
                    lambda rule, product=product: rule.product_id <= product,
                )
            )

    @api.depends("product_tmpl_id.write_date")
    def _compute_write_date(self):
        now = self.env.cr.now()
        self.fetch(["write_date"])
        for record in self:
            if not record.id:
                record.write_date = record._origin.write_date
                continue
            record.write_date = max(
                record.write_date or now,
                record.product_tmpl_id.write_date or now,
            )

    @api.depends("product_template_attribute_value_ids")
    def _compute_combination_indices(self):
        for product in self:
            product.combination_indices = (
                product.product_template_attribute_value_ids._ids2str()
            )

    def _compute_is_product_variant(self):
        self.is_product_variant = True

    @api.depends("product_template_attribute_value_ids.price_extra")
    def _compute_price_extra(self):
        for product in self:
            product.price_extra = sum(
                product.product_template_attribute_value_ids.mapped("price_extra"),
            )

    @api.depends("list_price", "price_extra")
    @api.depends_context("uom")
    def _compute_lst_price(self):
        to_uom = None
        if "uom" in self.env.context:
            to_uom = self.env["uom.uom"].browse(self.env.context["uom"])

        for product in self:
            price = product.list_price + product.price_extra
            if to_uom:
                price = product._convert_price_to_uom(price, to_uom)
            product.lst_price = price

    @api.depends_context("partner_id")
    @api.depends(
        "default_code",
        "seller_ids.partner_id",
        "seller_ids.product_code",
        "seller_ids.product_id",
    )
    def _compute_code(self):
        read_access = self.env["ir.model.access"].check(
            "product.supplierinfo",
            "read",
            False,
        )
        partner_id = self.env.context.get("partner_id")
        for product in self:
            product.code = product.default_code
            if read_access and partner_id:
                for supplier_info in product.seller_ids:
                    if supplier_info.partner_id.id == partner_id:
                        if (
                            supplier_info.product_id
                            and supplier_info.product_id != product
                        ):
                            continue
                        product.code = (
                            supplier_info.product_code or product.default_code
                        )
                        if product == supplier_info.product_id:
                            break

    @api.depends(
        "default_code",
        "name",
        "code",
        "display_name",
        "seller_ids.partner_id",
        "seller_ids.product_name",
    )
    @api.depends_context("partner_id")
    def _compute_partner_ref(self):
        partner_id = self.env.context.get("partner_id")
        for product in self:
            matched_seller = False
            if partner_id:
                matched_seller = next(
                    (
                        seller
                        for seller in product.seller_ids
                        if seller.partner_id.id == partner_id
                    ),
                    False,
                )
            if matched_seller:
                product_name = (
                    matched_seller.product_name or product.default_code or product.name
                )
                product.partner_ref = "%s%s" % (
                    (product.code and "[%s] " % product.code) or "",
                    product_name,
                )
            else:
                product.partner_ref = product.display_name

    @api.depends("product_tag_ids", "additional_product_tag_ids")
    def _compute_all_product_tag_ids(self):
        for product in self:
            product.all_product_tag_ids = (
                product.product_tag_ids | product.additional_product_tag_ids
            ).sorted("sequence")

    @api.depends_context(
        "company_id",
        "partner_id",
        "display_default_code",
        "seller_id",
        "formatted_display_name",
        "lang",
    )
    @api.depends("name", "default_code", "product_tmpl_id")
    def _compute_display_name(self):
        def get_display_name(name, code):
            if self.env.context.get("display_default_code", True) and code:
                if self.env.context.get("formatted_display_name"):
                    return f"{name}\t--{code}--"
                return f"[{code}] {name}"
            return name

        partner_id = self.env.context.get("partner_id")
        if partner_id:
            partner_ids = [
                partner_id,
                self.env["res.partner"].browse(partner_id).commercial_partner_id.id,
            ]
        else:
            partner_ids = []
        company_id = self.env.context.get("company_id")

        self.check_access("read")

        product_template_ids = self.sudo().product_tmpl_id.ids

        if partner_ids:
            supplier_info = (
                self.env["product.supplierinfo"]
                .sudo()
                .search_fetch(
                    [
                        ("product_tmpl_id", "in", product_template_ids),
                        ("partner_id", "in", partner_ids),
                    ],
                    [
                        "product_tmpl_id",
                        "product_id",
                        "company_id",
                        "product_name",
                        "product_code",
                    ],
                )
            )
            supplier_info_by_template = {}
            for r in supplier_info:
                supplier_info_by_template.setdefault(r.product_tmpl_id, []).append(r)

        context_sellers = (
            self.env["product.supplierinfo"]
            .sudo()
            .browse(self.env.context.get("seller_id"))
            or []
        )

        for product in self.sudo():
            variant = (
                product.product_template_attribute_value_ids._get_combination_name()
            )

            name = (variant and "%s (%s)" % (product.name, variant)) or product.name
            sellers = context_sellers
            if not sellers and partner_ids:
                product_supplier_info = supplier_info_by_template.get(
                    product.product_tmpl_id,
                    [],
                )
                sellers = [
                    x
                    for x in product_supplier_info
                    if x.product_id and x.product_id == product
                ]
                if not sellers:
                    sellers = [x for x in product_supplier_info if not x.product_id]
                if company_id:
                    sellers = [
                        x for x in sellers if x.company_id.id in [company_id, False]
                    ]
            if sellers:
                temp = []
                for s in sellers:
                    seller_variant = (
                        s.product_name
                        and (
                            (variant and "%s (%s)" % (s.product_name, variant))
                            or s.product_name
                        )
                    ) or False
                    temp.append(
                        get_display_name(
                            seller_variant or name,
                            s.product_code or product.default_code,
                        ),
                    )

                product.display_name = ", ".join(unique(temp))
            else:
                product.display_name = get_display_name(name, product.default_code)

    def _inverse_import_attribute_values(self):
        raise UserError(
            self.env._("This field can only be used to import products."),
        )

    def _inverse_pricelist_rule_ids(self):
        for product in self:
            template = product.product_tmpl_id
            template.pricelist_rule_ids = (
                product.pricelist_rule_ids
                | template.pricelist_rule_ids.filtered(
                    lambda rule, product=product: (
                        rule.product_id and rule.product_id != product
                    ),
                )
            )

    def _inverse_image_1920(self):
        return self._set_template_field("image_1920", "image_variant_1920")

    @api.model
    def _search(self, domain, *args, **kwargs):
        if self.env.context.get("search_default_categ_id"):
            domain = Domain(domain) & Domain(
                "categ_id",
                "child_of",
                self.env.context["search_default_categ_id"],
            )
        return super()._search(domain, *args, **kwargs)

    @api.model
    def _search_display_name(self, operator, value):
        is_positive = operator not in Domain.NEGATIVE_OPERATORS
        template_domains = [[("name", operator, value)]]
        product_domains = [[("default_code", operator, value)]]

        if operator == "in":
            product_domains.append([("barcode", "in", value)])
            product_domains.extend(
                [("default_code", "=", m.group(2))]
                for v in value
                if isinstance(v, str) and (m := re.search(r"(\[(.*?)\])", v))
            )
        elif operator.endswith("like") and is_positive:
            product_domains.append([("barcode", "in", [value])])

        supplier_domain = []
        if partner_id := self.env.context.get("partner_id"):
            supplier_domain = [
                ("partner_id", "=", partner_id),
                "|",
                ("product_code", operator, value),
                ("product_name", operator, value),
            ]

        if operator in Domain.NEGATIVE_OPERATORS:
            domains = template_domains + product_domains
            if supplier_domain:
                domains.append([("product_tmpl_id.seller_ids", "any", supplier_domain)])
            return Domain.AND(domains)

        self_no_active_test = self.with_context(active_test=False)
        queries = [
            self_no_active_test._search(
                [
                    (
                        "product_tmpl_id",
                        "in",
                        self_no_active_test.env["product.template"]._search(
                            Domain.OR(template_domains)
                        ),
                    ),
                ],
            ),
            self_no_active_test._search(Domain.OR(product_domains)),
        ]
        if supplier_domain:
            queries.append(
                self_no_active_test._search(
                    [
                        (
                            "product_tmpl_id",
                            "in",
                            self_no_active_test.env["product.supplierinfo"]
                            ._search(supplier_domain)
                            .subselect("product_tmpl_id"),
                        ),
                    ],
                ),
            )
        query = SQL(
            """(%s)""",
            SQL("UNION ALL").join([SQL("(%s)", query.select()) for query in queries]),
        )

        return [("id", "in", query)]

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        if not name:
            return super().name_search(name, domain, operator, limit)
        positive_operators = ["=", "ilike", "=ilike", "like", "=like"]
        is_positive = operator not in Domain.NEGATIVE_OPERATORS
        products = self.browse()
        domain = Domain(domain or Domain.TRUE)
        if operator in positive_operators:
            products = self.search_fetch(
                domain & Domain("default_code", "=", name),
                ["display_name"],
                limit=limit,
            ) or self.search_fetch(
                domain & Domain("barcode", "=", name),
                ["display_name"],
                limit=limit,
            )
        if not products:
            if is_positive:
                products = self.search_fetch(
                    domain & Domain("default_code", operator, name),
                    ["display_name"],
                    limit=limit,
                )
                limit_rest = None if limit is None else limit - len(products)
                if limit_rest is None or limit_rest > 0:
                    # This branch only runs when the default_code search did not
                    # reach `limit`, so `products` already holds every matching
                    # default_code row: reuse its ids instead of re-issuing the
                    # same search as an exclusion subquery.
                    products |= self.search_fetch(
                        domain
                        & Domain("id", "not in", products.ids)
                        & Domain("name", operator, name),
                        ["display_name"],
                        limit=limit_rest,
                    )
            else:
                domain_neg = Domain("name", operator, name) & (
                    Domain("default_code", operator, name)
                    | Domain("default_code", "=", False)
                )
                products = self.search_fetch(
                    domain & domain_neg,
                    ["display_name"],
                    limit=limit,
                )
        if (
            not products
            and operator in positive_operators
            and (m := re.search(r"(\[(.*?)\])", name))
        ):
            match_domain = Domain("default_code", "=", m.group(2))
            products = self.search_fetch(
                domain & match_domain,
                ["display_name"],
                limit=limit,
            )
        if not products and (partner_id := self.env.context.get("partner_id")):
            supplier_domain = Domain(
                [
                    ("partner_id", "=", partner_id),
                    "|",
                    ("product_code", operator, name),
                    ("product_name", operator, name),
                ],
            )
            match_domain = Domain("product_tmpl_id.seller_ids", "any", supplier_domain)
            products = self.search_fetch(
                domain & match_domain,
                ["display_name"],
                limit=limit,
            )
        return [(product.id, product.display_name) for product in products.sudo()]

    def _search_all_product_tag_ids(self, operator, operand):
        if operator in Domain.NEGATIVE_OPERATORS:
            return NotImplemented
        return [
            "|",
            ("product_tag_ids", operator, operand),
            ("additional_product_tag_ids", operator, operand),
        ]

    def _search_is_in_selected_section_of_order(self, operator, value):
        if operator != "in":
            return NotImplemented
        ctx = self.env.context
        order_id = ctx.get("order_id")
        order_model = ctx.get("product_catalog_order_model")
        line_field = ctx.get("child_field")
        if not (order_id and order_model and line_field):
            return []

        if order_model not in self.env.registry or not isinstance(
            self.env[order_model], self.env.registry["mixin.product.catalog"]
        ):
            raise UserError(
                self.env._("The product catalog cannot be used on this model."),
            )
        field = self.env[order_model]._fields.get(line_field)
        if field is None or field.type != "one2many":
            raise UserError(
                self.env._("%s is not a line field of the order.", line_field),
            )

        product_ids = (
            self.env[order_model]
            .browse(order_id)[line_field]
            .filtered(
                lambda line: line.get_line_parent_section().id == ctx.get("section_id"),
            )
            .mapped("product_id")
            .ids
        )

        return [("id", "in", product_ids)]

    @api.onchange("lst_price")
    def _inverse_lst_price(self):
        for product in self:
            if self.env.context.get("uom"):
                uom = self.env["uom.uom"].browse(self.env.context["uom"])
                value = product._convert_price_from_uom(product.lst_price, uom)
            else:
                value = product.lst_price
            value -= product.price_extra
            product.write({"list_price": value})

    @api.onchange("default_code")
    def _onchange_default_code(self):
        if not self.default_code:
            return None

        domain = [("default_code", "=", self.default_code)]
        if self.id.origin:
            domain.append(("id", "!=", self.id.origin))

        if self.env["product.product"].search_count(domain, limit=1):
            return {
                "warning": {
                    "title": self.env._("Note:"),
                    "message": self.env._(
                        "The Internal Reference '%s' already exists.",
                        self.default_code,
                    ),
                },
            }
        return None

    @api.onchange("uom_id")
    def _onchange_uom_id(self):
        if (
            self._origin.uom_id == self.uom_id
            or not self._is_uom_change_warning_required()
        ):
            return None
        message = self.env._(
            "Changing the unit of measure for your product will apply a conversion 1 %(old_uom_name)s = 1 %(new_uom_name)s.\n"
            "All existing records (Sales orders, Purchase orders, etc.) using this product will be updated by replacing the unit name.",
            old_uom_name=self._origin.uom_id.display_name,
            new_uom_name=self.uom_id.display_name,
        )
        return {
            "warning": {
                "title": self.env._("What to expect ?"),
                "message": message,
            },
        }

    @api.model
    def view_header_get(self, view_id, view_type):
        if self.env.context.get("categ_id"):
            return self.env._(
                "Products: %(category)s",
                category=self.env["product.category"]
                .browse(self.env.context["categ_id"])
                .name,
            )
        return super().view_header_get(view_id, view_type)

    def action_archive(self):
        records = self.filtered("active")
        super().action_archive()
        records.product_tmpl_id.filtered(
            lambda product_tmpl: (
                product_tmpl.active and not product_tmpl.product_variant_ids
            ),
        ).action_archive()

    def action_unarchive(self):
        records = self.filtered(lambda rec: not rec.active)
        super().action_unarchive()
        records.product_tmpl_id.filtered(
            lambda product_tmpl: (
                not product_tmpl.active and product_tmpl.product_variant_ids
            ),
        ).action_unarchive()

    @api.readonly
    def action_view_label_layout(self):
        if any(product.type == "service" for product in self):
            raise ValidationError(
                self.env._("Labels cannot be printed for products of service type"),
            )
        action = self.env["ir.actions.act_window"]._get_action_dict_by_xml_id(
            "product.action_view_label_layout",
        )
        action["context"] = {"default_product_ids": self.ids}
        return action

    def action_open_packaging_barcodes(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Packaging Barcodes"),
            "res_model": "product.uom",
            "view_mode": "list",
            "view_id": self.env.ref("product.product_uom_list_view").id,
            "domain": [("product_id", "=", self.id)],
            "context": {
                "default_product_id": self.id,
                "product_ids": self.ids,
            },
        }

    def view_product_template(self):
        self.check_singleton()
        return {
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "form",
            "res_id": self.product_tmpl_id.id,
            "target": "new",
        }

    def _filtered_to_unlink(self):
        return self

    def get_contextual_price(self):
        return self._get_contextual_price()

    def _get_contextual_price(self):
        self.check_singleton()
        return self.product_tmpl_id._get_contextual_price(self)

    def _get_contextual_discount(self):
        self.check_singleton()

        pricelist = self.product_tmpl_id._get_contextual_pricelist()
        if not pricelist:
            return 0.0

        date = self.env.context.get("date") or fields.Datetime.now()
        lst_price = self.currency_id._convert(
            self.lst_price,
            pricelist.currency_id,
            self.env.company,
            date,
            round=False,
        )
        if lst_price:
            return (lst_price - self._get_contextual_price()) / lst_price
        return 0.0

    def _get_invoice_policy(self):
        return False

    def _get_placeholder_filename(self, field):
        if field in tuple("image_%s" % size for size in IMAGE_SIZES):
            return self._get_product_placeholder_filename()
        return super()._get_placeholder_filename(field)

    def _get_product_placeholder_filename(self):
        return self.product_tmpl_id._get_product_placeholder_filename()

    def _get_barcodes_by_company(self):
        return [
            (company_id, [p.barcode for p in products if p.barcode])
            for company_id, products in groupby(self, lambda p: p.company_id.id)
        ]

    def _get_domain_barcode_search(self, barcodes_within_company, company_id):
        domain = [("barcode", "in", barcodes_within_company)]
        if company_id:
            domain.append(("company_id", "in", (False, company_id)))
        return domain

    def _get_filtered_sellers(
        self,
        partner_id=False,
        quantity=0.0,
        date=None,
        uom_id=False,
        params=False,
    ):
        self.check_singleton()
        if not date:
            date = fields.Date.context_today(self)
        precision = self.env["decimal.precision"].get_precision("Product Unit")

        sellers_filtered = self._prepare_sellers(params)
        matching_ids = []
        for seller in sellers_filtered:
            if seller.date_start and seller.date_start > date:
                continue
            if seller.date_end and seller.date_end < date:
                continue
            if (
                params
                and params.get("force_uom")
                and seller.product_uom_id not in (uom_id, self.uom_id)
            ):
                continue
            if partner_id and seller.partner_id not in [
                partner_id,
                partner_id.parent_id,
            ]:
                continue
            if seller.product_id and seller.product_id != self:
                continue
            if quantity is not None:
                quantity_uom_seller = quantity
                if quantity_uom_seller and uom_id and uom_id != seller.product_uom_id:
                    if not uom_id._has_common_reference(seller.product_uom_id):
                        continue
                    quantity_uom_seller = uom_id._get_quantity_in_unit(
                        quantity_uom_seller,
                        seller.product_uom_id,
                    )
                if (
                    float_compare(
                        quantity_uom_seller,
                        seller.min_qty,
                        precision_digits=precision,
                    )
                    == -1
                ):
                    continue
            matching_ids.append(seller.id)
        return self.env["product.supplierinfo"].browse(matching_ids)

    def _prepare_product_price_context(self, combination):
        self.check_singleton()
        res = {}

        no_variant_attributes_price_extra = self._get_no_variant_attributes_price_extra(
            combination,
        )

        if no_variant_attributes_price_extra:
            res["no_variant_attributes_price_extra"] = no_variant_attributes_price_extra

        return res

    def _get_no_variant_attributes_price_extra(self, combination):
        return sum(
            ptav.price_extra
            for ptav in combination.filtered(
                lambda ptav: (
                    ptav.price_extra
                    and ptav.product_tmpl_id == self.product_tmpl_id
                    and ptav not in self.product_template_attribute_value_ids
                ),
            )
        )

    def _get_attributes_extra_price(self):
        self.check_singleton()

        return self.price_extra + self.env.context.get(
            "no_variant_attributes_price_extra",
            0,
        )

    @api.model
    def get_empty_list_help(self, help_message):
        self = self.with_context(
            empty_list_help_document_name=self.env._("product"),
        )
        return super().get_empty_list_help(help_message)

    def get_product_multiline_description_sale(self):
        name = self.display_name
        if self.description_sale:
            name += "\n" + self.description_sale

        return name

    @api.model
    def load(self, fields, data):
        if "import_attribute_values" in fields and not self.env.context.get(
            "from_template_import"
        ):
            res = self.env["product.template"].load(fields, data)
            res["ids"] = self.search(Domain("product_tmpl_id", "in", res["ids"])).ids
            return res
        return super().load(fields, data)

    def _load_records_write(self, values):
        import_attribute_values = values.get("import_attribute_values", "")
        if not import_attribute_values:
            return super()._load_records_write(values)

        def split(values):
            return {
                tuple(part.strip() for part in attr.split(":"))
                for attr in values.split(",")
            }

        attribute_values = split(import_attribute_values)
        existing_values = split(self.import_attribute_values)

        if attribute_values != existing_values:
            raise ValidationError(
                self.env._(
                    'The existing product has different attribute values. "%(imported_values)s" is not equivalent to "%(existing_values)s" for "%(external_id)s", "%(id)s"',
                    imported_values=import_attribute_values,
                    existing_values=self.import_attribute_values,
                    external_id=self.get_external_id()[self.id],
                    id=self.id,
                )
            )

        values = {
            key: val
            for key, val in values.items()
            if val and key != "import_attribute_values"
        }

        return super()._load_records_write(values)

    def _parse_import_attribute_values(self, raw):
        parsed = []
        seen_attributes = set()
        for token in raw.split(","):
            attribute_name, value_name = (
                token.split(":", 1) if ":" in token else (None, token)
            )
            attribute_name = attribute_name and attribute_name.strip()
            value_name = value_name.strip()
            if not attribute_name:
                raise ValueError(  # noqa: E8511  the import wizard shows this text
                    self.env._(
                        "Unable to import products with attribute value without attribute name (defined as: attribute:value): %s",
                        raw,
                    )
                )
            if attribute_name in seen_attributes:
                raise ValueError(  # noqa: E8511  the import wizard shows this text
                    self.env._(
                        "It is not possible to import different values for the same attribute: %s",
                        raw,
                    )
                )
            seen_attributes.add(attribute_name)
            parsed.append((attribute_name, value_name))
        return parsed

    def _load_records_create(self, data_list):
        with_import_values = [
            vals for vals in data_list if vals.get("import_attribute_values")
        ]
        without_import_values = [
            vals for vals in data_list if not vals.get("import_attribute_values")
        ]
        if not with_import_values:
            return super()._load_records_create(data_list)

        imported_product = super()._load_records_create(without_import_values)
        rows = self._import_read_rows(with_import_values)

        contexted = self.sudo().with_context(
            create_product_product=False,
            update_product_template_attribute_values=True,
        )

        pa_pav_records = contexted._import_resolve_attribute_values(rows)
        id2template, name2template, product_templates, created_templates = (
            contexted._import_resolve_templates(rows)
        )
        default_values = self._import_template_defaults(
            rows, product_templates + created_templates
        )

        for row in rows:
            row["target_template_id"] = (
                row["product_tmpl_id"] or name2template[row["name"]].id
            )

        useless_products = contexted.env["product.product"].search(
            Domain("product_tmpl_id", "in", [row["target_template_id"] for row in rows])
            & Domain("product_template_attribute_value_ids", "=", False)
        )
        useless_products._unlink_or_archive()

        template_value_to_ptav = contexted._import_resolve_ptavs(
            rows,
            id2template,
            name2template,
            pa_pav_records,
        )
        products = super()._load_records_create(
            [
                self._import_variant_values(
                    row,
                    default_values,
                    template_value_to_ptav,
                    pa_pav_records,
                )
                for row in rows
            ]
        )

        return imported_product.exists() + products

    def _import_read_rows(self, with_import_values):
        rows = []
        for vals in with_import_values:
            name = (vals.get("name") or "").strip()
            if not name and not vals.get("product_tmpl_id"):
                raise ValueError(  # noqa: E8511  the import wizard shows this text
                    self.env._(
                        "Unable to import products with attribute values but without name of product set"
                    )
                )
            rows.append(
                {
                    "values": vals,
                    "name": name,
                    "product_tmpl_id": vals.get("product_tmpl_id"),
                    "parsed": self._parse_import_attribute_values(
                        vals["import_attribute_values"]
                    ),
                }
            )
        return rows

    def _import_template_defaults(self, rows, templates):
        field_names = [
            name
            for name in unique(key for row in rows for key in row["values"])
            if name in self._fields
        ]
        return {
            values["product_tmpl_id"][0]: values
            for values in templates.product_variant_id.read(
                fields=["product_tmpl_id"] + field_names
            )
        }

    def _import_variant_values(
        self, row, default_values, template_value_to_ptav, pa_pav_records
    ):
        template_id = row["target_template_id"]
        defaults = default_values.get(template_id) or {}
        values = {}
        for key, value in row["values"].items():
            if key in ("import_attribute_values", "id", "name"):
                continue
            if value:
                values[key] = value
                continue
            field = self._fields.get(key)
            if field is not None and field.inherited:
                continue
            values[key] = defaults.get(key, False)
        values["product_tmpl_id"] = template_id
        values["product_template_attribute_value_ids"] = [
            template_value_to_ptav[
                template_id,
                pa_pav_records[attribute_name, value_name].id,
            ].id
            for attribute_name, value_name in row["parsed"]
        ]
        return values

    def _import_resolve_attribute_values(self, rows):
        PA = self.env["product.attribute"]
        PAV = self.env["product.attribute.value"]

        attribute_to_values = defaultdict(OrderedSet)
        for row in rows:
            for attribute_name, value_name in row["parsed"]:
                attribute_to_values[attribute_name].add(value_name)

        pa_records = {
            pa.name: pa
            for pa in PA.search(Domain("name", "in", list(attribute_to_values)))
        }
        missing_pa = [
            {
                "name": attribute_name,
                "create_variant": "dynamic",
                "display_type": "radio",
            }
            for attribute_name in attribute_to_values
            if attribute_name not in pa_records
        ]
        if missing_pa:
            for pa in PA.create(missing_pa):
                pa_records[pa.name] = pa

        pa_pav_records = {}
        domain = Domain(False)
        for attribute_name, value_names in attribute_to_values.items():
            domain |= Domain("name", "in", value_names) & Domain(
                "attribute_id.name", "=", attribute_name
            )
        for pav in PAV.search(domain):
            pa_records[pav.attribute_id.name] = pav.attribute_id
            pa_pav_records[pav.attribute_id.name, pav.name] = pav

        missing_pav = [
            {
                "name": value_name,
                "attribute_id": pa_records[attribute_name].id,
            }
            for attribute_name, value_names in attribute_to_values.items()
            for value_name in value_names
            if (attribute_name, value_name) not in pa_pav_records
        ]
        if missing_pav:
            for pav in PAV.create(missing_pav):
                pa_pav_records[pav.attribute_id.name, pav.name] = pav

        return pa_pav_records

    def _import_resolve_templates(self, rows):
        PT = self.env["product.template"]

        product_templates = PT.search(
            Domain("name", "in", [row["name"] for row in rows])
            | Domain("id", "in", [row["product_tmpl_id"] for row in rows])
        )
        id2template = dict(zip(product_templates.ids, product_templates, strict=True))
        name2template = dict(
            zip(product_templates.mapped("name"), product_templates, strict=True)
        )

        template_vals_list = {}
        for row in rows:
            name = row["name"]
            if name and name not in name2template and name not in template_vals_list:
                template_vals_list[name] = {
                    key: value
                    for key, value in row["values"].items()
                    if (field := PT._fields.get(key)) is not None and field.required
                }

        created_templates = PT.with_context(create_product_product=True).create(
            list(template_vals_list.values())
        )
        for rec in created_templates:
            id2template[rec.id] = rec
            name2template[rec.name] = rec

        return id2template, name2template, product_templates, created_templates

    def _import_resolve_ptavs(
        self,
        rows,
        id2template,
        name2template,
        pa_pav_records,
    ):
        PTAL = self.env["product.template.attribute.line"]

        pt_to_attribute_to_values = defaultdict(list)
        for row in rows:
            pt = id2template.get(row["product_tmpl_id"]) or name2template.get(
                row["name"]
            )
            for attribute_name, value_name in row["parsed"]:
                pav = pa_pav_records[attribute_name, value_name]
                pt_to_attribute_to_values[pt.id, pav.attribute_id.id].append(pav)
        domain = Domain(False)
        for template_id, attribute_id in pt_to_attribute_to_values:
            domain |= Domain("product_tmpl_id", "=", template_id) & Domain(
                "attribute_id", "=", attribute_id
            )
        template_attribute_to_ptal = {
            (ptal.product_tmpl_id.id, ptal.attribute_id.id): ptal
            for ptal in PTAL.search(domain)
        }
        ptals_to_create = []
        for (template_id, attribute_id), pavs in pt_to_attribute_to_values.items():
            ptal = template_attribute_to_ptal.get((template_id, attribute_id))
            if ptal:
                ptal.value_ids = ptal.value_ids.union(*pavs)
            else:
                ptals_to_create.append(
                    {
                        "product_tmpl_id": template_id,
                        "attribute_id": attribute_id,
                        "value_ids": [value.id for value in pavs],
                    }
                )
        if ptals_to_create:
            ptals = PTAL.create(ptals_to_create)
            template_attribute_to_ptal.update(
                dict(
                    zip(
                        [
                            (val["product_tmpl_id"], val["attribute_id"])
                            for val in ptals_to_create
                        ],
                        ptals,
                        strict=True,
                    )
                )
            )

        return {
            (template_id, pav.id): template_attribute_to_ptal[
                template_id, attribute_id
            ].product_template_value_ids.filtered(
                lambda v, pav=pav: v.product_attribute_value_id.id == pav.id
            )
            for (template_id, attribute_id), pavs in pt_to_attribute_to_values.items()
            for pav in pavs
        }

    def _prepare_sellers(self, params=False):
        all_sellers = self.sudo().variant_seller_ids
        sellers = all_sellers._filtered_for_company_and_product(
            self.env.company, self, params
        )
        return sellers.sorted(lambda s: (s.sequence, -s.min_qty, s.price, s.id))

    def _select_seller(
        self,
        partner_id=False,
        quantity=0.0,
        date=None,
        uom_id=False,
        ordered_by="price_discounted",
        params=False,
    ):
        sort_key = ("price_discounted", "sequence", "id")
        if ordered_by != "price_discounted":
            sort_key = (ordered_by, "price_discounted", "sequence", "id")

        def sort_function(record):
            vals = {
                "price_discounted": record.currency_id._convert(
                    record.price_discounted,
                    record.env.company.currency_id,
                    record.env.company,
                    date or fields.Date.context_today(self),
                    round=False,
                ),
            }
            return [vals.get(key, record[key]) for key in sort_key]

        sellers = self._get_filtered_sellers(
            partner_id=partner_id,
            quantity=quantity,
            date=date,
            uom_id=uom_id,
            params=params,
        )
        res_ids = []
        res_partner = None
        for seller in sellers:
            if not res_ids or res_partner == seller.partner_id:
                res_ids.append(seller.id)
                res_partner = seller.partner_id
        res = self.env["product.supplierinfo"].browse(res_ids)
        return res and res.sorted(sort_function)[:1]

    def _set_template_field(self, template_field, variant_field):
        tmpl_ids = self.product_tmpl_id.ids
        variant_counts = {}
        if tmpl_ids:
            data = self.env["product.product"]._read_group(
                [("product_tmpl_id", "in", tmpl_ids), ("active", "=", True)],
                ["product_tmpl_id"],
                ["__count"],
            )
            variant_counts = {tmpl.id: count for tmpl, count in data}
        for record in self:
            if (
                (not record[template_field] and not record[variant_field])
                or (
                    record[template_field]
                    and not record.product_tmpl_id[template_field]
                )
                or variant_counts.get(record.product_tmpl_id.id, 0) <= 1
            ):
                record[variant_field] = False
                record.product_tmpl_id[template_field] = record[template_field]
            else:
                record[variant_field] = record[template_field]

    def _is_uom_change_warning_required(self):
        return False

    def _unlink_or_archive(self, check_access=True):
        if check_access:
            self.check_access("unlink")
            self.check_access("write")
            self = self.sudo()
            to_unlink = self._filtered_to_unlink()
            to_archive = self - to_unlink
            to_archive.write({"active": False})
            self = to_unlink

        undeletable = unlink_where_possible(self, lambda products: products.unlink())
        undeletable.filtered("active").write({"active": False})

    def _is_variant_possible(self, parent_combination=None):
        self.check_singleton()
        return self.product_tmpl_id._is_combination_possible(
            self.product_template_attribute_value_ids,
            parent_combination=parent_combination,
            ignore_no_variant=True,
        )

    def _update_uom(self, to_uom_id):
        return True

    def _restamp_uom(
        self,
        model,
        to_uom_id,
        domain=None,
        product_field="product_id",
        context=None,
    ):
        # sudo: re-stamping the unit on documents that already reference the
        # product is a consistency consequence of a write the caller was allowed
        # to make on the product itself. Requiring read access to every module's
        # documents as well would stop a product manager from changing a unit at
        # all -- _has_order_lines already probes the same rows this way.
        Model = self.env[model].sudo()
        if domain is None:
            domain = [("product_id", "in", self.ids)]
        to_write = Model.browse()
        for uom, product, records in Model._read_group(
            domain, ["product_uom_id", product_field], ["id:recordset"]
        ):
            template = (
                product
                if product._name == "product.template"
                else product.product_tmpl_id
            )
            if uom != template.uom_id:
                raise UserError(
                    self.env._(
                        "Other units of measure (e.g., %(problem_uom)s) have already "
                        "been used for this product. The unit of measure cannot be "
                        "changed from %(uom)s. If you want to change it, please "
                        "archive the product and create a new one.",
                        problem_uom=uom.display_name,
                        uom=template.uom_id.display_name,
                    ),
                )
            to_write |= records
        if to_write:
            if context:
                to_write = to_write.with_context(**context)
            to_write.product_uom_id = to_uom_id
        return to_write

    def _check_duplicated_product_barcodes(self, barcodes_within_company, company_id):
        domain = self._get_domain_barcode_search(barcodes_within_company, company_id)
        products_by_barcode = self.sudo()._read_group(
            domain,
            ["barcode"],
            ["id:recordset"],
            having=[("__count", ">", 1)],
        )

        duplicates_as_str = "\n".join(
            self.env._(
                '- Barcode "%(barcode)s" already assigned to product(s): %(product_list)s',
                barcode=barcode,
                product_list=duplicate_products._filtered_access("read").mapped(
                    "display_name",
                ),
            )
            for barcode, duplicate_products in products_by_barcode
        )
        if duplicates_as_str:
            duplicates_as_str += self.env._(
                "\n\nNote: products that you don't have access to will not be shown above.",
            )
            raise ValidationError(
                self.env._("Barcode(s) already assigned:\n\n%s", duplicates_as_str),
            )

    def _check_duplicated_packaging_barcodes(self, barcodes_within_company, company_id):
        packaging_domain = self._get_domain_barcode_search(
            barcodes_within_company,
            company_id,
        )
        if self.env["product.uom"].sudo().search_count(packaging_domain, limit=1):
            raise ValidationError(self.env._("A packaging already uses the barcode"))
