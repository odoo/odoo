# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
from collections import OrderedDict
from urllib.parse import urlencode, urlparse

from odoo import api, fields, models
from odoo.http import request

_logger = logging.getLogger(__name__)


class ProductProduct(models.Model):
    _name = 'product.product'
    _inherit = ["product.product", "website.structured_data.mixin"]
    _mail_post_access = "read"

    # === DEFAULT METHODS ===#

    @api.model
    def _default_website_sequence(self):
        self.env.cr.execute("SELECT MAX(website_sequence) FROM %s" % self._table)
        max_sequence = self.env.cr.fetchone()[0]
        if max_sequence is None:
            return 10000
        return max_sequence + 5

    # === FIELDS ===#

    variant_ribbon_id = fields.Many2one(string="Variant Ribbon", comodel_name="product.ribbon")
    website_id = fields.Many2one(related="product_tmpl_id.website_id", readonly=False)

    product_variant_image_ids = fields.One2many(
        string="Extra Variant Images",
        comodel_name="product.image",
        inverse_name="product_variant_id",
    )

    website_url = fields.Char(
        string="Website URL",
        help="The full URL to access the document through the website.",
        compute="_compute_product_website_url",
    )

    stock_notification_partner_ids = fields.Many2many(
        "res.partner",
        relation="stock_notification_product_partner_rel",
        string="Back in stock Notifications",
    )
    website_sequence = fields.Integer(
        string="Website Sequence",
        help="Determine the display order of variants in the Website eCommerce",
        default=_default_website_sequence,
        copy=False,
        index=True,
    )
    website_size_x = fields.Integer(string="Size X", default=1)
    website_size_y = fields.Integer(string="Size Y", default=1)

    # === COMPUTE METHODS ===#

    @api.depends_context("lang")
    @api.depends("product_tmpl_id.website_url", "product_template_attribute_value_ids")
    def _compute_product_website_url(self):
        slug = self.env["ir.http"]._slug
        for product in self:
            url = urlparse(product.product_tmpl_id.website_url)
            if pavs := product.product_template_attribute_value_ids.product_attribute_value_id:
                # There's no need to group the PAVs by attribute since a product variant can have
                # only one PAV per attribute.
                query_params = {slug(pav.attribute_id): slug(pav) for pav in pavs}
                url = url._replace(query=urlencode(query_params))
            product.website_url = url.geturl()

    # === SEQUENCE METHODS ===#

    def _init_column(self, column_name):
        # to avoid generating a single default website_sequence when installing the module,
        # we need to set the default row by row for this column
        if column_name == "website_sequence":
            _logger.debug(
                "Table '%s': setting default value of new column %s to unique values for each row",
                self._table,
                column_name,
            )
            self.env.cr.execute("SELECT id FROM %s WHERE website_sequence IS NULL" % self._table)
            prod_ids = self.env.cr.dictfetchall()
            max_seq = self._default_website_sequence()
            query = f"""
                UPDATE {self._table}
                SET website_sequence = p.web_seq
                FROM (VALUES %s) AS p(p_id, web_seq)
                WHERE id = p.p_id
            """
            values_args = [(prod["id"], max_seq + i * 5) for i, prod in enumerate(prod_ids)]
            self.env.cr.execute_values(query, values_args)
        else:
            super()._init_column(column_name)

    def set_sequence_top(self):
        min_sequence = self.sudo().search([], order="website_sequence ASC", limit=1)
        self.website_sequence = min_sequence.website_sequence - 5

    def set_sequence_bottom(self):
        max_sequence = self.sudo().search([], order="website_sequence DESC", limit=1)
        self.website_sequence = max_sequence.website_sequence + 5

    def set_sequence_up(self):
        previous_product = self.sudo().search(
            [
                ("website_sequence", "<", self.website_sequence),
                ("website_published", "=", self.website_published),
            ],
            order="website_sequence DESC",
            limit=1,
        )
        if previous_product:
            previous_product.website_sequence, self.website_sequence = (
                self.website_sequence,
                previous_product.website_sequence,
            )
        else:
            self.set_sequence_top()

    def set_sequence_down(self):
        next_product = self.sudo().search(
            [
                ("website_sequence", ">", self.website_sequence),
                ("website_published", "=", self.website_published),
            ],
            order="website_sequence ASC",
            limit=1,
        )
        if next_product:
            next_product.website_sequence, self.website_sequence = (
                self.website_sequence,
                next_product.website_sequence,
            )
        else:
            self.set_sequence_bottom()

    # === BUSINESS METHODS ===#

    def website_publish_button(self):
        self.ensure_one()
        return self.product_tmpl_id.website_publish_button()

    def open_website_url(self):
        self.ensure_one()
        res = self.product_tmpl_id.open_website_url()
        res["url"] = self.website_url
        return res

    def action_unschedule(self):
        """Keep variants aligned with their template scheduling."""
        return self.product_tmpl_id.action_unschedule()

    def _get_images(self):
        """Return a list of records implementing `image.mixin` to
        display on the carousel on the website for this variant.

        This returns a list and not a recordset because the records might be
        from different models (template, variant and image).

        It contains in this order: the main image of the variant (which will fall back on the main
        image of the template, if unset), the Variant Extra Images, and the Template Extra Images.
        """
        self.ensure_one()
        variant_images = list(self.product_variant_image_ids)
        template_images = list(self.product_tmpl_id.product_template_image_ids)
        return [self] + variant_images + template_images

    def _get_combination_info_variant(self, **kwargs):
        """Return the variant info based on its combination.
        See `_get_combination_info` for more information.
        """
        self.ensure_one()
        return self.product_tmpl_id._get_combination_info(
            combination=self.product_template_attribute_value_ids, product_id=self.id, **kwargs
        )

    def _get_sales_prices(self, pricelist_sudo, fiscal_position_sudo, website):
        """Variant-level equivalent of product.template._get_sales_prices."""
        if not self:
            return {}

        currency = website.currency_id
        pricelist_prices = pricelist_sudo._compute_price_rule(self, 1.0)
        comparison_prices_enabled = self.env["res.groups"]._is_feature_enabled(
            "website_sale.group_product_price_comparison"
        )
        uom_price_enabled = self.env["res.groups"]._is_feature_enabled(
            "product.group_show_uom_price"
        )

        res = {}
        for product in self:
            pricelist_price, pricelist_rule_id = pricelist_prices[product.id]

            product_taxes = product.sudo().taxes_id._filter_taxes_by_company()
            taxes = fiscal_position_sudo.map_tax(product_taxes)

            base_price = None
            product_price_vals = {
                "raw_pricelist_price": pricelist_price,
                "pricelist_rule_id": pricelist_rule_id,
                "price_reduce": product._apply_taxes_to_price(
                    pricelist_price,
                    currency,
                    product_taxes=product_taxes,
                    taxes=taxes,
                    website=website,
                ),
            }
            pricelist_item_sudo = (
                product.env["product.pricelist.item"].sudo().browse(pricelist_rule_id)
            )
            if pricelist_item_sudo._show_discount_on_shop():
                pricelist_base_price = pricelist_item_sudo._compute_price_before_discount(
                    product=product,
                    quantity=1.0,
                    uom=product.product_tmpl_id._get_main_uom(),
                    currency=currency,
                )
                if currency.compare_amounts(pricelist_base_price, pricelist_price) == 1:
                    base_price = pricelist_base_price
                    product_price_vals["base_price"] = product._apply_taxes_to_price(
                        base_price,
                        currency,
                        product_taxes=product_taxes,
                        taxes=taxes,
                        website=website,
                    )
            if not base_price and comparison_prices_enabled and product.compare_list_price:
                product_price_vals["base_price"] = product.currency_id._convert(
                    product.compare_list_price, currency, self.env.company, round=False
                )

            if uom_price_enabled:
                product_price_vals["base_unit_price"] = product._get_base_unit_price(
                    product_price_vals["price_reduce"]
                )

            res[product.id] = product_price_vals

        return res

    def _website_show_quick_add(self):
        self.ensure_one()
        if self._is_sold_out() or not self.filtered_domain(self.env["website"]._product_domain()):
            return False
        if not self._get_available_uoms():
            return False
        return not (
            self.env.website.prevent_sale
            and self.env.website._prevent_product_sale(self, not self._get_contextual_price())
        )

    def _is_add_to_cart_allowed(self):
        self.ensure_one()
        if self.env.user.has_group("base.group_system"):
            return True
        if self._is_donation():
            return True
        if not self.active or not self.website_published:
            return False
        if not self.filtered_domain(self.env["website"]._product_domain()):
            return False
        website = self.env.website
        if website.prevent_sale and website._prevent_product_sale(
            self, not self._get_contextual_price()
        ):
            return False
        return website.has_ecommerce_access()

    @api.onchange("public_categ_ids")
    def _onchange_public_categ_ids(self):
        if self.public_categ_ids:
            self.website_published = True
        else:
            self.website_published = False

    def _prepare_jsonld_vals(self):
        """JSON-LD payload describing the variant as a https://schema.org/Product."""
        self.ensure_one()

        website = self.env.website or self.env['website'].browse(self.env.context.get('host_id'))
        base_url = website.get_base_url()
        product_price = request.pricelist._get_product_price(
            self, quantity=1, currency=website.currency_id
        )
        # Use sudo to access cross-company taxes.
        price = self._apply_taxes_to_price(product_price, website.currency_id, website=website)

        offer = {
            "@type": "Offer",
            "price": price,
            "priceCurrency": website.currency_id.name,
        }
        if self.is_product_variant and self.is_storable:
            offer["availability"] = (
                "https://schema.org/OutOfStock" if self._is_sold_out()
                else "https://schema.org/InStock"
            )

        vals = {
            "@type": "Product",
            "@id": f"{base_url}{self.website_url}/#product-{self.id}",
            "name": self.with_context(display_default_code=False).display_name,
            "url": f"{base_url}{self.website_url}",
            "offers": offer,
            "image": f"{base_url}{self._get_image_1920_url()}",
        }
        if description := (self.website_meta_description or self.description_sale):
            vals["description"] = description
        if self.barcode:
            vals["gtin"] = self.barcode

        direct, others = self._split_standard_from_custom_attributes()
        vals.update(direct)
        if others:
            vals["additionalProperty"] = [
                {"@type": "PropertyValue", "name": name, "value": value}
                for name, value in others.items()
            ]
        return vals

    def _get_image_1920_url(self):
        """Return the local url of the product main image.

        Note: self.ensure_one()

        :rtype: str
        """
        self.ensure_one()
        return self.env["website"].image_url(self, "image_1920")

    def _get_extra_image_1920_urls(self):
        """Return the local url of the product additional images, no videos. This includes the
        variant specific images first and then the template images.

        Note: self.ensure_one()

        :rtype: list[str]
        """
        self.ensure_one()
        return [
            self.env["website"].image_url(extra_image, "image_1920")
            for extra_image in self.product_variant_image_ids + self.product_template_image_ids
            if extra_image.image_128  # only images, no video urls
        ]

    def write(self, vals):
        if "active" in vals and not vals["active"]:
            # unlink draft lines containing the archived product
            self.env["sale.order.line"].sudo().search([
                ("state", "=", "draft"),
                ("product_id", "in", self.ids),
                ("order_id", "any", [("website_id", "!=", False)]),
            ]).unlink()
        return super().write(vals)

    def _is_in_wishlist(self):
        if not self:
            return False
        self.ensure_one()
        return self in self.env["product.wishlist"].current().mapped("product_id")

    def _prepare_categories_for_display(self):
        """On the comparison page group on the same line the values of each
        product that concern the same attributes, and then group those
        attributes per category.

        The returned categories are ordered following their default order.

        :return: OrderedDict [{
            product.attribute.category: OrderedDict [{
                product.attribute: OrderedDict [{
                    product: [product.template.attribute.value]
                }]
            }]
        }]
        """
        attributes = (
            self.product_tmpl_id.valid_product_template_attribute_line_ids.attribute_id.sorted()
        )
        categories = OrderedDict([(cat, OrderedDict()) for cat in attributes.category_id.sorted()])
        if any(not pa.category_id for pa in attributes):
            # category_id is not required and the mapped does not return empty
            categories[self.env["product.attribute.category"]] = OrderedDict()
        for pa in attributes:
            categories[pa.category_id][pa] = OrderedDict([
                (
                    product,
                    product.product_template_attribute_value_ids.filtered(
                        lambda ptav: ptav.attribute_id == pa
                    )  # If no_variant, show all possible values
                    or product.attribute_line_ids.filtered(
                        lambda ptal: ptal.attribute_id == pa
                    ).value_ids,
                )
                for product in self
            ])
        return categories

    def _get_image_1024_url(self):
        """Return the local url of the product main image.

        Note: self.ensure_one()
        :rtype: str
        """
        self.ensure_one()
        return self.env["website"].image_url(self, "image_1024")

    def _has_multiple_uoms(self) -> bool:
        """Check if the product has multiple available uoms for the current website.

        :return: True if the product has multiple available uoms for the current website
                 or if the default uom is not available
        """
        res = super()._has_multiple_uoms()
        if res:
            return res
        if self.env.context.get("website_id") and self.type != "combo":
            uoms = self._get_available_uoms()
            if uoms:
                return self.uom_id not in uoms
        return res

    def _get_available_uoms(self):
        """Return a recordset of uoms configured for the product that are available for the current
        website.

        :returns: uoms available on the product for the current website.
        :rtype: recordset of `uom.uom`
        """
        all_uoms = super()._get_available_uoms()
        if self.env["res.groups"]._is_feature_enabled("uom.group_uom") and self.env.context.get(
            "website_id"
        ):
            return all_uoms - self.env.website.restricted_uom_ids
        return all_uoms

    def _get_main_uom(self):
        """Return the main uom for the product.
        The main uom is always the first available uom on the current website, if no uom is
        available, the default uom configured on the product is considered as the main uom.

        :returns: the main uom of the product
        :rtype: `uom.uom` recordset
        """
        self.ensure_one()
        if self.env.context.get("website_id"):
            return self._get_available_uoms()[:1] or self.uom_id
        return super()._get_main_uom()

    def _get_extra_tracking_values(self, **kwargs):
        extra_tracking_values = {}
        if kwargs.get("res_model") == self._name and (res_id := kwargs.get("res_id")):
            extra_tracking_values["product_id"] = res_id
        return extra_tracking_values

    def _is_donation(self):
        """Return whether this product is the donation product used by the donation snippet."""
        self.ensure_one()
        # Unpublished, sudo to allow public users to read it
        return self.sudo().product_tmpl_id._is_donation()

    def _is_sold_out(self):
        """Return whether the product is sold out (no available quantity).

        If a product inventory is not tracked, or if it's allowed to be sold regardless
        of availabilities, the product is never considered sold out.

        :return: whether the product can still be sold
        :rtype: bool
        """
        self.ensure_one()
        if not self.is_storable or self.allow_out_of_stock_order:
            return False
        free_qty = self.env.website._get_product_available_qty(self.sudo())
        return free_qty <= 0

    def _has_stock_notification(self, partner):
        self.ensure_one()
        return partner in self.stock_notification_partner_ids

    def _get_max_quantity(self, website, sale_order, **kwargs):
        """Return The max quantity of a product.
        It is the difference between the quantity that's free to use and the quantity that's already
        been added to the cart.

        Note: self.ensure_one()

        :param website website: The website for which to compute the max quantity.
        :return: The max quantity of the product.
        :rtype: float | None
        """
        self.ensure_one()
        if self.is_storable and not self.allow_out_of_stock_order:
            free_qty = website._get_product_available_qty(self.sudo(), **kwargs)
            cart_qty = sale_order._get_cart_qty(self.id)
            return free_qty - cart_qty
        return None

    def _send_availability_email(self):
        products = self.search([("stock_notification_partner_ids", "!=", False)]).filtered(
            lambda p: not p._is_sold_out()
        )
        self.env["ir.cron"]._commit_progress(remaining=len(products.stock_notification_partner_ids))
        email_template = self.env.ref(
            "website_sale.email_template_back_in_stock", raise_if_not_found=False
        )
        if not email_template:
            return
        for product_id in products.ids:
            product = self.env["product.product"].browse(product_id)
            for partner_id in product.with_context(
                # Only fetch the ids, all the other fields will be invalidated either way
                prefetch_fields=False
            ).stock_notification_partner_ids.ids:
                partner = self.env["res.partner"].browse(partner_id)
                email_template.with_user(self.env.website.salesperson_id).with_context(
                    customer_name=partner.name, lang=partner.lang
                ).send_mail(
                    product.id,
                    force_send=True,
                    email_values={
                        "email_to": partner.email_formatted,
                        "email_from": self.env.website.company_id.partner_id.email_formatted,
                    },
                )

                product.stock_notification_partner_ids -= partner
                self.env["ir.cron"]._commit_progress(1)

    def _split_standard_from_custom_attributes(self):
        self.ensure_one()
        return self.product_template_attribute_value_ids._split_standard_from_custom_attributes()

    def _apply_taxes_to_price(self, *args, **kwargs):
        self.ensure_one()
        return self.product_tmpl_id._apply_taxes_to_price(*args, product=self, **kwargs)
