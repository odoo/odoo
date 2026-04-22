# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import api, fields, models
from odoo.http import request


class ProductProduct(models.Model):
    _inherit = "product.product"
    _mail_post_access = "read"

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

    # === COMPUTE METHODS ===#

    @api.depends_context("lang")
    @api.depends("product_tmpl_id.website_url", "product_template_attribute_value_ids")
    def _compute_product_website_url(self):
        for product in self:
            url = product.product_tmpl_id.website_url
            if pavs := product.product_template_attribute_value_ids.product_attribute_value_id:
                pav_ids = [str(pav.id) for pav in pavs]
                url = f"{url}?attribute_values={','.join(pav_ids)}"
            product.website_url = url

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

    def _website_show_quick_add(self):
        self.ensure_one()
        if self._is_sold_out() or not self.filtered_domain(self.env["website"]._product_domain()):
            return False
        if not self._get_available_uoms():
            return False
        website = self.env["website"].get_current_website()
        return not (
            website.prevent_sale
            and website._prevent_product_sale(self, not self._get_contextual_price())
        )

    def _is_add_to_cart_allowed(self):
        self.ensure_one()
        if self.env.user.has_group("base.group_system"):
            return True
        if not self.active or not self.website_published:
            return False
        if not self.filtered_domain(self.env["website"]._product_domain()):
            return False
        website = self.env["website"].get_current_website()
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

    def _to_markup_data(self, website):
        """Generate JSON-LD markup data for the current product.

        :param website website: The current website.
        :return: The JSON-LD markup data.
        :rtype: dict
        """
        self.ensure_one()

        product_price = request.pricelist._get_product_price(
            self, quantity=1, currency=website.currency_id
        )
        # Use sudo to access cross-company taxes.
        product_taxes_sudo = self.sudo().taxes_id._filter_taxes_by_company(self.env.company)
        taxes = request.fiscal_position.map_tax(product_taxes_sudo)
        price = self.product_tmpl_id._apply_taxes_to_price(
            product_price, website.currency_id, product_taxes_sudo, taxes, self, website=website
        )

        base_url = website.get_base_url()
        markup_data = {
            "@context": "https://schema.org",
            "@type": "Product",
            "name": self.with_context(display_default_code=False).display_name,
            "url": f"{base_url}{self.website_url}",
            "image": f"{base_url}{website.image_url(self, 'image_1920')}",
            "offers": {"@type": "Offer", "price": price, "priceCurrency": website.currency_id.name},
        }
        if self.website_meta_description or self.description_sale:
            markup_data["description"] = self.website_meta_description or self.description_sale
        if self.barcode:
            markup_data["gtin"] = self.barcode
        if self.is_product_variant and self.is_storable:
            if not self._is_sold_out():
                availability = "https://schema.org/InStock"
            else:
                availability = "https://schema.org/OutOfStock"
            markup_data["offers"]["availability"] = availability
        return markup_data

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
            return all_uoms - self.env["website"].get_current_website().restricted_uom_ids
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
        if (
            kwargs.get('res_model') == self._name
            and (res_id := kwargs.get('res_id'))
        ):
            extra_tracking_values['product_id'] = res_id
        return extra_tracking_values

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
        free_qty = self.env["website"].get_current_website()._get_product_available_qty(self.sudo())
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
        website = self.env["website"].get_current_website()
        for product_id in products.ids:
            product = self.env["product.product"].browse(product_id)
            for partner_id in product.with_context(
                # Only fetch the ids, all the other fields will be invalidated either way
                prefetch_fields=False
            ).stock_notification_partner_ids.ids:
                partner = self.env["res.partner"].browse(partner_id)
                email_template.with_user(website.salesperson_id).with_context(
                    customer_name=partner.name, lang=partner.lang
                ).send_mail(
                    product.id,
                    force_send=True,
                    email_values={
                        "email_to": partner.email_formatted,
                        "email_from": website.company_id.partner_id.email_formatted,
                    },
                )

                product.stock_notification_partner_ids -= partner
                self.env["ir.cron"]._commit_progress(1)
