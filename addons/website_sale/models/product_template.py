import logging
from collections import defaultdict
from urllib.parse import urlencode

from odoo import _, api, fields, models
from odoo.db import FunctionStatus
from odoo.db.schema import column_exists, create_column
from odoo.fields import Domain
from odoo.http import request
from odoo.libs.debug_log import DebugLog
from odoo.libs.sql import SQL
from odoo.tools import float_is_zero, is_html_empty
from odoo.tools.translate import html_translate

from odoo.addons.website.models import ir_http
from odoo.addons.website.tools import text_from_html
from odoo.addons.website_sale.const import SHOP_PATH

RARE_DELIMITER = "\u241e"

_logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


def get_translated_field_gist_index(registry, column_name):
    if not registry.has_trigram:
        return ""
    if registry.has_unaccent == FunctionStatus.INDEXABLE:
        return f"USING GIST(unaccent((JSONB_PATH_QUERY_ARRAY({column_name}, '$.*'::jsonpath))::text) gist_trgm_ops)"
    return f"USING GIST((JSONB_PATH_QUERY_ARRAY({column_name}, '$.*'::jsonpath)::text) gist_trgm_ops)"


class ProductTemplate(models.Model):
    _name = "product.template"
    _inherit = [
        "mixin.rating",
        "product.template",
        "mixin.website.seo.metadata",
        "mixin.website.published.multi",
        "mixin.website.searchable",
    ]
    _mail_post_access = "read"
    _check_company_auto = True

    @api.model
    def _default_website_sequence(self):
        self.env.cr.execute("SELECT MAX(website_sequence) FROM %s" % self._table)
        max_sequence = self.env.cr.fetchone()[0]
        if max_sequence is None:
            return 10000
        return max_sequence + 5

    website_description = fields.Html(
        string="Description for the website",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
        index="trigram",
    )
    description_ecommerce = fields.Html(
        string="eCommerce Description",
        translate=html_translate,
        sanitize_overridable=True,
        sanitize_attributes=False,
        sanitize_form=False,
    )

    alternative_product_ids = fields.Many2many(
        comodel_name="product.template",
        relation="product_alternative_rel",
        column1="src_id",
        column2="dest_id",
        string="Alternative Products",
        check_company=True,
        help="Suggest alternatives to your customer (upsell strategy)."
        " Those products show up on the product page.",
    )
    accessory_product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="product_accessory_rel",
        column1="src_id",
        column2="dest_id",
        string="Accessory Products",
        check_company=True,
        help="Accessories show up when the customer reviews the cart before payment"
        " (cross-sell strategy).",
    )

    website_size_x = fields.Integer(
        string="Size X",
        default=1,
    )
    website_size_y = fields.Integer(
        string="Size Y",
        default=1,
    )
    website_ribbon_id = fields.Many2one(
        comodel_name="product.ribbon",
        string="Ribbon",
    )
    website_sequence = fields.Integer(
        default=_default_website_sequence,
        index=True,
        copy=False,
        help="Determine the display order in the Website E-commerce",
    )
    public_categ_ids = fields.Many2many(
        comodel_name="product.public.category",
        relation="product_public_category_product_template_rel",
        string="Website Product Category",
        help="The product will be available in each mentioned eCommerce category. Go to Shop > Edit"
        " Click on the page and enable 'Categories' to view all eCommerce categories.",
    )

    publish_date = fields.Datetime(
        compute="_compute_publish_date",
        precompute=True,
        store=True,
    )

    product_template_image_ids = fields.One2many(
        comodel_name="product.image",
        inverse_name="product_tmpl_id",
        string="Extra Product Media",
        copy=True,
    )

    base_unit_count = fields.Float(
        compute="_compute_base_unit_count",
        inverse="_inverse_base_unit_count",
        default=0,
        store=True,
        required=True,
        help="Display base unit price on your eCommerce pages. Set to 0 to hide it for this product.",
    )
    base_unit_id = fields.Many2one(
        comodel_name="website.base.unit",
        string="Custom Unit of Measure",
        compute="_compute_base_unit_id",
        inverse="_inverse_base_unit_id",
        store=True,
        help="Define a custom unit to display in the price per unit of measure field.",
    )
    base_unit_price = fields.Monetary(
        string="Price Per Unit",
        compute="_compute_base_unit_price",
    )
    base_unit_name = fields.Char(
        compute="_compute_base_unit_name",
        help="Displays the custom unit for the products if defined or the selected unit of measure"
        " otherwise.",
    )

    compare_list_price = fields.Monetary(
        string="Compare to Price",
        help="Add a strikethrough price to your /shop and product pages for comparison purposes."
        "It will not be displayed if pricelists apply.",
    )
    variants_default_code = fields.Char(
        compute="_compute_variants_default_code",
        store=True,
        index="trigram",
        help="Technical field to enhance performance when looking up default code of product"
        "variants (LIKE/ILIKE)",
    )
    description = fields.Html(index="trigram")
    description_sale = fields.Text(index="trigram")

    _name_gist_idx = models.Index(
        lambda registry: get_translated_field_gist_index(registry, "name")
    )
    _description_gist_idx = models.Index(
        lambda registry: get_translated_field_gist_index(registry, "description")
    )
    _description_sale_gist_idx = models.Index(
        lambda registry: get_translated_field_gist_index(registry, "description_sale")
    )
    _default_code_gist_idx = models.Index(
        lambda registry: (
            "USING GIST(unaccent(default_code) gist_trgm_ops)"
            if registry.has_trigram
            and registry.has_unaccent == FunctionStatus.INDEXABLE
            else (
                "USING GIST(default_code gist_trgm_ops)" if registry.has_trigram else ""
            )
        )
    )

    def _auto_init(self):
        if not column_exists(self.env.cr, "product_template", "variants_default_code"):
            create_column(
                self.env.cr, "product_template", "variants_default_code", "varchar"
            )
            self.env.cr.execute(
                SQL(
                    """
                    UPDATE product_template
                    SET variants_default_code = variants.default_codes
                    FROM (
                        SELECT pt.id AS template_id,
                               STRING_AGG(pv.default_code, %s) AS default_codes
                        FROM product_template pt
                        JOIN product_product pv ON pv.product_tmpl_id = pt.id
                        WHERE pv.default_code IS NOT NULL
                        GROUP BY pt.id
                    ) AS variants
                    WHERE product_template.id = variants.template_id
                """,
                    RARE_DELIMITER,
                )
            )
        return super()._auto_init()

    @api.depends("is_published")
    def _compute_publish_date(self):
        now = fields.Datetime.now()
        for template in self:
            if template.is_published or not template.publish_date:
                template.publish_date = now

    @api.depends("product_variant_ids", "product_variant_ids.base_unit_count")
    def _compute_base_unit_count(self):
        self.base_unit_count = 0
        for template in self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        ):
            template.base_unit_count = template.product_variant_ids.base_unit_count

    def _inverse_base_unit_count(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.base_unit_count = template.base_unit_count

    @api.depends("product_variant_ids", "product_variant_ids.base_unit_count")
    def _compute_base_unit_id(self):
        self.base_unit_id = self.env["website.base.unit"]
        for template in self.filtered(
            lambda template: len(template.product_variant_ids) == 1
        ):
            template.base_unit_id = template.product_variant_ids.base_unit_id

    def _inverse_base_unit_id(self):
        for template in self:
            if len(template.product_variant_ids) == 1:
                template.product_variant_ids.base_unit_id = template.base_unit_id

    def _get_base_unit_price(self, price):
        self.check_singleton()
        return self.base_unit_count and price / self.base_unit_count

    @api.depends("list_price", "base_unit_count")
    def _compute_base_unit_price(self):
        for template in self:
            template.base_unit_price = template._get_base_unit_price(
                template.list_price
            )

    @api.depends("uom_name", "base_unit_id.name")
    def _compute_base_unit_name(self):
        for template in self:
            template.base_unit_name = template.base_unit_id.name or template.uom_name

    def _compute_website_url(self):
        super()._compute_website_url()
        for product in self:
            if product.id:
                product.website_url = "/shop/%s" % self.env["ir.http"]._slug(product)

    @api.depends("product_variant_ids.default_code")
    def _compute_variants_default_code(self):
        for template in self:
            template.variants_default_code = RARE_DELIMITER.join(
                template.product_variant_ids.filtered("default_code").mapped(
                    "default_code"
                )
            )

    def write(self, vals):
        if (
            (description_ecommerce := vals.get("description_ecommerce"))
            and is_html_empty(description_ecommerce)
            and not (
                "media_iframe_video" in description_ecommerce
                or "data-embedded" in description_ecommerce
            )
        ):
            vals["description_ecommerce"] = ""
        return super().write(vals)

    def _prepare_variant_values(self, combination):
        variant_dict = super()._prepare_variant_values(combination)
        variant_dict["base_unit_count"] = self.base_unit_count
        return variant_dict

    def _get_website_accessory_product(self):
        domain = Domain(self.env["website"].sale_product_domain())
        if not self.env.user._is_internal():
            domain &= Domain("is_published", "=", True)
        return self.accessory_product_ids.filtered_domain(domain)

    def _get_website_alternative_product(self):
        domain = self.env["website"].sale_product_domain()
        return self.alternative_product_ids.filtered_domain(domain)

    def _has_no_variant_attributes(self):
        self.check_singleton()
        return any(
            a.create_variant == "no_variant"
            for a in self.valid_product_template_attribute_line_ids.attribute_id
        )

    def _has_is_custom_values(self):
        self.check_singleton()
        return any(
            v.is_custom
            for v in self.valid_product_template_attribute_line_ids.product_template_value_ids._filtered_active()
        )

    def _get_possible_variants_sorted(self, parent_combination=None):
        self.check_singleton()

        def _sort_key_attribute_value(value):
            return (value.attribute_id.sequence, value.attribute_id.id)

        def _sort_key_variant(variant):
            keys = []
            for attribute in variant.product_template_attribute_value_ids.sorted(
                _sort_key_attribute_value
            ):
                keys.append(attribute.product_attribute_value_id.sequence)
                keys.append(attribute.id)
            return keys

        return self._get_possible_variants(parent_combination).sorted(_sort_key_variant)

    def _get_previewed_attribute_values(self, category=None, product_query_params=None):
        res = defaultdict(dict)
        show_count = 20
        for template in self:
            previewed_ptal = next(
                (
                    p
                    for p in template.attribute_line_ids
                    if p.attribute_id.preview_variants != "hidden"
                ),
                None,
            )
            if previewed_ptal:
                previewed_ptavs = [
                    ptav
                    for ptav in previewed_ptal.product_template_value_ids
                    if ptav.ptav_active and ptav.ptav_product_variant_ids
                ]

                if len(previewed_ptavs) > 1:
                    previewed_ptavs_data = []
                    for ptav in previewed_ptavs[:show_count]:
                        matching_variant = min(
                            ptav.ptav_product_variant_ids, key=lambda p: p.id
                        )
                        variant_query_params = {
                            **(product_query_params or {}),
                            "attribute_values": str(ptav.product_attribute_value_id.id),
                        }
                        previewed_ptavs_data.append(
                            {
                                "ptav": ptav,
                                "variant_image_url": self.env["website"].image_url(
                                    matching_variant, "image_512"
                                ),
                                "variant_url": template._get_product_url(
                                    category, variant_query_params
                                ),
                            }
                        )

                    res[template.id] = {
                        "ptavs_data": previewed_ptavs_data,
                        "hidden_ptavs_count": max(0, len(previewed_ptavs) - show_count),
                    }
        return res

    def _get_sales_prices(self, website):
        if not self:
            return {}

        pricelist = request.pricelist
        currency = website.currency_id
        fiscal_position_sudo = request.fiscal_position
        date = fields.Date.context_today(self)

        pricelist_prices = pricelist._get_price_rule(self, 1.0)
        comparison_prices_enabled = self.env["res.groups"]._is_feature_enabled(
            "website_sale.group_product_price_comparison"
        )

        res = {}
        for template in self:
            pricelist_price, pricelist_rule_id = pricelist_prices[template.id]

            product_taxes = template.sudo().taxes_id._filter_taxes_by_company(
                self.env.company
            )
            taxes = fiscal_position_sudo.map_tax(product_taxes)

            base_price = None
            template_price_vals = {
                "price_reduce": self._apply_taxes_to_price(
                    pricelist_price,
                    currency,
                    product_taxes,
                    taxes,
                    template,
                    website=website,
                ),
            }
            pricelist_item = template.env["product.pricelist.item"].browse(
                pricelist_rule_id
            )
            if pricelist_item._show_discount_on_shop():
                pricelist_base_price = pricelist_item._get_price_before_discount(
                    product=template,
                    quantity=1.0,
                    date=date,
                    uom=template.uom_id,
                    currency=currency,
                )
                if currency.compare_amounts(pricelist_base_price, pricelist_price) == 1:
                    _debug.logic(
                        "shop_base_price",
                        by="pricelist_discount",
                        template=template.id,
                        rule=pricelist_rule_id,
                    )
                    base_price = pricelist_base_price
                    template_price_vals["base_price"] = self._apply_taxes_to_price(
                        base_price,
                        currency,
                        product_taxes,
                        taxes,
                        template,
                        website=website,
                    )

            if (
                not base_price
                and comparison_prices_enabled
                and template.compare_list_price
            ):
                _debug.logic(
                    "shop_base_price", by="compare_list_price", template=template.id
                )
                template_price_vals["base_price"] = template.currency_id._convert(
                    template.compare_list_price,
                    currency,
                    self.env.company,
                    date,
                    round=False,
                )

            res[template.id] = template_price_vals

        _debug.perf.count(
            "shop_prices_computed",
            templates=len(self),
            pricelist=pricelist.id,
            comparison=comparison_prices_enabled,
        )
        return res

    def _can_be_added_to_cart(self):
        self.check_singleton()
        return bool(self.filtered_domain(self.env["website"]._product_domain()))

    def _is_add_to_cart_possible(self, parent_combination=None):
        self.check_singleton()
        if not self.active or not self._can_be_added_to_cart():
            _debug.logic(
                "add_to_cart_impossible", reason="not_sellable", template=self.id
            )
            return False
        return (
            next(self._get_possible_combinations(parent_combination), False)
            is not False
        )

    def _get_combination_info(
        self,
        combination=False,
        product_id=False,
        add_qty=1.0,
        uom_id=False,
        only_template=False,
    ):
        self.check_singleton()

        combination = combination or self.env["product.template.attribute.value"]
        website = request.website.with_context(self.env.context)
        uom = self.env["uom.uom"].browse(uom_id) or self.uom_id

        if not product_id and not combination and not only_template:
            combination = self._get_first_possible_combination()

        if only_template:
            product = self.env["product.product"]
        elif product_id:
            product = self.env["product.product"].browse(product_id)
            if combination - product.product_template_attribute_value_ids:
                product = self._get_variant_for_combination(combination)
        else:
            product = self._get_variant_for_combination(combination)

        product_or_template = product or self
        combination = combination or product.product_template_attribute_value_ids

        display_name = product_or_template.with_context(
            display_default_code=False
        ).display_name
        if not product:
            combination_name = combination._get_combination_name()
            if combination_name:
                display_name = f"{display_name} ({combination_name})"

        price_context = product_or_template._prepare_product_price_context(combination)
        product_or_template = product_or_template.with_context(**price_context)

        combination_info = {
            "combination": combination,
            "product_id": product.id,
            "product_template_id": self.id,
            "display_name": display_name,
            "is_combination_possible": self._is_combination_possible(
                combination=combination
            ),
            **self._get_additionnal_combination_info(
                product_or_template=product_or_template,
                quantity=add_qty or 1.0,
                uom=uom,
                date=fields.Date.context_today(self),
                website=website,
            ),
        }

        if website.google_analytics_key:
            combination_info["product_tracking_info"] = self._get_google_analytics_data(
                product,
                combination_info,
            )

        if (
            product_or_template.type == "combo"
            and website.show_line_subtotals_tax_selection == "tax_included"
            and not all(
                tax.price_include
                for tax in product_or_template.sudo().combo_ids.combo_item_ids.product_id.taxes_id
            )
        ):
            combination_info["tax_disclaimer"] = _(
                "Final price may vary based on selection. Tax will be calculated at checkout."
            )

        return combination_info

    def _add_compare_list_price(
        self, combination_info, product_or_template, currency, date, has_discount
    ):
        if (
            not has_discount
            and product_or_template.compare_list_price
            and self.env["res.groups"]._is_feature_enabled(
                "website_sale.group_product_price_comparison"
            )
        ):
            _debug.logic("combination_compare_price", product=product_or_template.id)
            combination_info["compare_list_price"] = (
                product_or_template.currency_id._convert(
                    from_amount=product_or_template.compare_list_price,
                    to_currency=currency,
                    company=self.env.company,
                    date=date,
                    round=False,
                )
            )

    def _get_additionnal_combination_info(
        self, product_or_template, quantity, uom, date, website
    ):
        pricelist = request.pricelist.with_context(self.env.context)
        currency = website.currency_id.with_context(self.env.context)

        pricelist_price, pricelist_rule_id = pricelist._get_product_price_rule(
            product=product_or_template,
            quantity=quantity,
            uom=uom,
            currency=currency,
        )

        price_before_discount = pricelist_price
        pricelist_item = self.env["product.pricelist.item"].browse(pricelist_rule_id)
        if pricelist_item._show_discount_on_shop():
            price_before_discount = pricelist_item._get_price_before_discount(
                product=product_or_template,
                quantity=quantity or 1.0,
                date=date,
                uom=uom,
                currency=currency,
            )

        has_discounted_price = (
            currency.compare_amounts(price_before_discount, pricelist_price) == 1
        )
        _debug.logic(
            "combination_price", rule=pricelist_rule_id, discounted=has_discounted_price
        )
        combination_info = {
            "list_price": max(pricelist_price, price_before_discount),
            "price": pricelist_price,
            "has_discounted_price": has_discounted_price,
            "discount_start_date": pricelist_item.date_start,
            "discount_end_date": pricelist_item.date_end,
        }

        self._add_compare_list_price(
            combination_info, product_or_template, currency, date, has_discounted_price
        )

        product_taxes = product_or_template.sudo().taxes_id._filter_taxes_by_company(
            self.env.company
        )
        taxes = self.env["account.tax"]
        if product_taxes:
            taxes = request.fiscal_position.map_tax(product_taxes)
            for price_key in ("price", "list_price"):
                combination_info[price_key] = self._apply_taxes_to_price(
                    combination_info[price_key],
                    currency,
                    product_taxes,
                    taxes,
                    product_or_template,
                    website=website,
                )

        combination_info.update(
            {
                "prevent_zero_price_sale": website.prevent_zero_price_sale
                and float_is_zero(
                    combination_info["price"],
                    precision_rounding=currency.rounding,
                ),
                "currency": currency,
                "date": date,
                "product_taxes": product_taxes,
                "taxes": taxes,
            }
        )

        if self.env["res.groups"]._is_feature_enabled(
            "website_sale.group_show_uom_price"
        ):
            price_per_product_uom = uom._get_price_in_unit(
                price=combination_info["price"], to_unit=self.uom_id
            )
            combination_info.update(
                {
                    "base_unit_name": product_or_template.base_unit_name,
                    "base_unit_price": product_or_template._get_base_unit_price(
                        price_per_product_uom
                    ),
                }
            )

        if combination_info["prevent_zero_price_sale"]:
            combination_info["compare_list_price"] = 0

        return combination_info

    @api.model
    def _apply_taxes_to_price(
        self,
        price,
        currency,
        product_taxes,
        taxes,
        product_or_template,
        website=None,
    ):
        website = website or self.env["website"].get_current_website()
        price = self.env["product.product"]._get_tax_included_unit_price_from_price(
            price,
            product_taxes,
            product_taxes_after_fp=taxes,
        )
        show_tax = website.show_line_subtotals_tax_selection
        tax_display = (
            "total_excluded" if show_tax == "tax_excluded" else "total_included"
        )

        return taxes.compute_all(
            price, currency, 1, product_or_template, self.env.user.partner_id
        )[tax_display]

    def create_product_variant(self, product_template_attribute_value_ids):
        combination = self.env["product.template.attribute.value"].browse(
            product_template_attribute_value_ids
        )

        return self._create_product_variant(combination, log_warning=True).id or 0

    def _get_image_holder(self):
        self.check_singleton()
        if self.image_128:
            return self
        variant = self.env["product.product"].browse(
            self._get_first_possible_variant_id()
        )
        return variant if variant.image_variant_128 else self

    def _get_suitable_image_size(self, columns, x_size, y_size):
        if x_size == 1 and y_size == 1 and columns >= 3:
            return "image_512"
        return "image_1024"

    def _init_column(self, column_name, *, new_column=False):
        if column_name == "website_sequence":
            _logger.debug(
                "Table '%s': setting default value of new column %s to unique values for each row",
                self._table,
                column_name,
            )
            self.env.cr.execute(
                "SELECT id FROM %s WHERE website_sequence IS NULL" % self._table
            )
            prod_tmpl_ids = self.env.cr.dictfetchall()
            max_seq = self._default_website_sequence()
            query = f"""
                UPDATE {self._table}
                SET website_sequence = p.web_seq
                FROM (VALUES %s) AS p(p_id, web_seq)
                WHERE id = p.p_id
            """
            values_args = [
                (prod_tmpl["id"], max_seq + i * 5)
                for i, prod_tmpl in enumerate(prod_tmpl_ids)
            ]
            self.env.cr.execute_values(query, values_args)
        else:
            super()._init_column(column_name, new_column=new_column)

    def set_sequence_top(self):
        min_sequence = self.sudo().search([], order="website_sequence ASC", limit=1)
        self.website_sequence = min_sequence.website_sequence - 5

    def set_sequence_bottom(self):
        max_sequence = self.sudo().search([], order="website_sequence DESC", limit=1)
        self.website_sequence = max_sequence.website_sequence + 5

    def set_sequence_up(self):
        previous_product_tmpl = self.sudo().search(
            [
                ("website_sequence", "<", self.website_sequence),
                ("website_published", "=", self.website_published),
            ],
            order="website_sequence DESC",
            limit=1,
        )
        if previous_product_tmpl:
            previous_product_tmpl.website_sequence, self.website_sequence = (
                self.website_sequence,
                previous_product_tmpl.website_sequence,
            )
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_prodcut_tmpl = self.search(
            [
                ("website_sequence", ">", self.website_sequence),
                ("website_published", "=", self.website_published),
            ],
            order="website_sequence ASC",
            limit=1,
        )
        if next_prodcut_tmpl:
            next_prodcut_tmpl.website_sequence, self.website_sequence = (
                self.website_sequence,
                next_prodcut_tmpl.website_sequence,
            )
        else:
            return self.set_sequence_bottom()
        return None

    def _get_default_website_meta(self):
        res = super()._get_default_website_meta()
        res["default_opengraph"]["og:description"] = res["default_twitter"][
            "twitter:description"
        ] = self.description_sale
        res["default_opengraph"]["og:title"] = res["default_twitter"][
            "twitter:title"
        ] = self.name
        res["default_opengraph"]["og:image"] = res["default_twitter"][
            "twitter:image"
        ] = self.env["website"].image_url(self, "image_1024")
        res["default_meta_description"] = self.description_sale
        return res

    @api.model
    def _get_alternative_product_filter(self):
        return self.env.ref(
            "website_sale.dynamic_filter_cross_selling_alternative_products"
        ).id

    @api.model
    def _get_product_types_allow_zero_price(self):
        return []

    def _get_domain_rating(self, record_ids=None):
        return super()._get_domain_rating(record_ids=record_ids) & Domain(
            "is_internal", "=", False
        )

    def _get_images(self):
        self.check_singleton()
        return [self] + list(self.product_template_image_ids)

    def _get_domain_attribute_value(self, attribute_value_dict):
        return [
            [("attribute_line_ids.value_ids", "in", attribute_value_ids)]
            for attribute_value_ids in attribute_value_dict.values()
        ]

    @api.model
    def _search_get_detail(self, website, order, options):
        with_image = options["displayImage"]
        with_description = options["displayDescription"]
        with_category = options["displayExtraLink"]
        with_price = options["displayDetail"]
        domains = [website.sale_product_domain()]
        category = options.get("category")
        tags = options.get("tags")
        min_price = options.get("min_price")
        max_price = options.get("max_price")
        attribute_value_dict = options.get("attribute_value_dict")
        if category:
            domains.append(
                [
                    (
                        "public_categ_ids",
                        "child_of",
                        self.env["ir.http"]._unslug(category)[1],
                    )
                ]
            )
        if tags:
            if isinstance(tags, str):
                tags = tags.split(",")
            tags = list(map(int, tags))
            domains.append(
                Domain.OR(
                    [
                        Domain("product_tag_ids", "in", tags),
                        Domain(
                            "product_variant_ids.additional_product_tag_ids", "in", tags
                        ),
                    ]
                )
            )
        if min_price:
            domains.append([("list_price", ">=", min_price)])
        if max_price:
            domains.append([("list_price", "<=", max_price)])
        if attribute_value_dict:
            domains.extend(self._get_domain_attribute_value(attribute_value_dict))
        search_fields = ["name", "default_code", "variants_default_code"]
        fetch_fields = ["id", "name", "website_url"]
        mapping = {
            "name": {"name": "name", "type": "text", "match": True},
            "default_code": {"name": "default_code", "type": "text", "match": True},
            "product_variant_ids.default_code": {
                "name": "product_variant_ids.default_code",
                "type": "text",
                "match": True,
            },
            "website_url": {"name": "website_url", "type": "text", "truncate": False},
        }
        if with_image:
            mapping["image_url"] = {"name": "image_url", "type": "html"}
        if with_description:
            search_fields.append("description")
            fetch_fields.append("description")
            search_fields.append("description_sale")
            fetch_fields.append("description_sale")
            mapping["description"] = {
                "name": "description_sale",
                "type": "text",
                "match": True,
            }
        if with_price:
            mapping["detail"] = {
                "name": "price",
                "type": "html",
                "display_currency": options["display_currency"],
            }
            mapping["detail_strike"] = {
                "name": "list_price",
                "type": "html",
                "display_currency": options["display_currency"],
            }
        if with_category:
            mapping["extra_link"] = {"name": "category", "type": "html"}
        return {
            "model": "product.template",
            "base_domain": domains,
            "search_fields": search_fields,
            "fetch_fields": fetch_fields,
            "mapping": mapping,
            "icon": "fa-shopping-cart",
        }

    def _search_render_results(self, fetch_fields, mapping, icon, limit):
        with_image = "image_url" in mapping
        with_category = "extra_link" in mapping
        with_price = "detail" in mapping
        results_data = super()._search_render_results(
            fetch_fields, mapping, icon, limit
        )
        current_website = self.env["website"].get_current_website()
        for product, data in zip(self, results_data, strict=False):
            categ_ids = product.public_categ_ids.filtered(
                lambda c: not c.website_id or c.website_id == current_website
            )
            if with_price:
                combination_info = product._get_combination_info(only_template=True)
                data["price"], list_price = self._search_render_results_prices(
                    mapping, combination_info
                )
                if list_price:
                    data["list_price"] = list_price

            if with_image:
                data["image_url"] = (
                    "/web/image/product.template/%s/image_128" % data["id"]
                )
            if with_category and categ_ids:
                data["category"] = (
                    self.env["ir.ui.view"]
                    .sudo()
                    ._render_template(
                        "website_sale.product_category_extra_link",
                        {
                            "categories": categ_ids,
                            "slug": self.env["ir.http"]._slug,
                            "shop_path": SHOP_PATH,
                        },
                    )
                )
        return results_data

    def _search_render_results_prices(self, mapping, combination_info):
        if combination_info.get("prevent_zero_price_sale"):
            return None, None

        monetary_options = {"display_currency": mapping["detail"]["display_currency"]}
        price = self.env["ir.qweb.field.monetary"].value_to_html(
            combination_info["price"], monetary_options
        )
        list_price = None
        if combination_info["has_discounted_price"]:
            list_price = self.env["ir.qweb.field.monetary"].value_to_html(
                combination_info["list_price"], monetary_options
            )
        if combination_info.get("compare_list_price"):
            list_price = self.env["ir.qweb.field.monetary"].value_to_html(
                combination_info["compare_list_price"], monetary_options
            )

        return price, list_price

    def _get_google_analytics_data(self, product, combination_info):
        self.check_singleton()
        return {
            "item_id": product.barcode or product.id,
            "item_name": combination_info["display_name"],
            "item_category": self.categ_id.name,
            "currency": combination_info["currency"].name,
            "price": combination_info["list_price"],
        }

    def _get_contextual_pricelist(self):
        pricelist = super()._get_contextual_pricelist()
        if request and request.is_frontend and not pricelist:
            return request.pricelist
        return pricelist

    def _website_show_quick_add(self):
        self.check_singleton()
        if not self.filtered_domain(self.env["website"]._product_domain()):
            return False
        return (
            not request.website.prevent_zero_price_sale or self._get_contextual_price()
        )

    @api.model
    def _get_configurator_display_price(
        self, product_or_template, quantity, date, currency, pricelist, **kwargs
    ):
        price, pricelist_rule_id = super()._get_configurator_display_price(
            product_or_template, quantity, date, currency, pricelist, **kwargs
        )

        if website := ir_http.get_request_website():
            product_taxes = (
                product_or_template.sudo().taxes_id._filter_taxes_by_company(
                    self.env.company
                )
            )
            if product_taxes:
                taxes = request.fiscal_position.map_tax(product_taxes)
                return self._apply_taxes_to_price(
                    price,
                    currency,
                    product_taxes,
                    taxes,
                    product_or_template,
                    website=website,
                ), pricelist_rule_id
        return price, pricelist_rule_id

    def _to_markup_data(self, website):
        self.check_singleton()

        if self.product_variant_count == 1:
            return self.product_variant_id._to_markup_data(website)

        limit = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("website_sale.markup_data_limit_variants", False)
        )
        if limit:
            product_variant_ids = self.product_variant_ids[: int(limit)]
        else:
            product_variant_ids = self.product_variant_ids

        base_url = website.get_base_url()
        markup_data = {
            "@context": "https://schema.org/",
            "@type": "ProductGroup",
            "name": self.name,
            "image": f"{base_url}{website.image_url(self, 'image_1920')}",
            "url": f"{base_url}{self.website_url}",
            "hasVariant": [
                product._to_markup_data(website) for product in product_variant_ids
            ],
        }
        if self.description_ecommerce:
            markup_data["description"] = text_from_html(self.description_ecommerce)
        return markup_data

    def _get_ribbon(self, price_vals=None, auto_assign_ribbons=None, variant=None):
        variant = variant or self.product_variant_id
        ribbon = variant.sudo().variant_ribbon_id or self.sudo().website_ribbon_id
        if not ribbon:
            if auto_assign_ribbons is None:
                auto_assign_ribbons = self.env["product.ribbon"].search_fetch(
                    [
                        ("assign", "!=", "manual"),
                    ]
                )
            for rb in auto_assign_ribbons:
                if rb._is_applicable_for(variant, price_vals):
                    return rb

        return ribbon

    def _get_access_action(self, access_uid=None, force_website=False):
        self.check_singleton()
        if force_website or (self.website_published and self.env.user.share):
            return {
                "type": "ir.actions.act_url",
                "url": self.website_url,
                "target": "self",
                "target_type": "public",
            }
        return super()._get_access_action(
            access_uid=access_uid, force_website=force_website
        )

    @api.model
    def _allow_publish_rating_stats(self):
        return True

    def _get_product_url(
        self, category=None, query_params=None, grouped_attributes_values=None
    ):
        self.check_singleton()
        slug = self.env["ir.http"]._slug

        url = (category and f"/shop/{slug(category)}/{slug(self)}") or self.website_url

        query_params = query_params or {}
        if grouped_attributes_values:
            product_grouped_values = self.attribute_line_ids.value_ids.grouped(
                "attribute_id"
            )
            available_pav_ids = [
                next(v.id for v in pavs if v in product_grouped_values[pa])
                for pa, pavs in grouped_attributes_values.items()
                if pa in product_grouped_values
            ]
            available_pav_ids.sort()
            query_params["attribute_values"] = ",".join(
                str(i) for i in available_pav_ids
            )

        if query_params:
            url = f"{url}?{urlencode(query_params)}"

        return url
