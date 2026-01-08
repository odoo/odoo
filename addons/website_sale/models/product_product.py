# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict
from urllib.parse import urlencode, urlparse

from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError
from odoo.fields import Domain
from odoo.http import request


class ProductProduct(models.Model):
    _name = "product.product"
    _inherit = ["product.product", "website.structured_data.mixin", "website.trackable.mixin"]
    _website_track_field = "product_id"
    _mail_post_access = "read"

    variant_ribbon_id = fields.Many2one(string="Variant Ribbon", comodel_name="product.ribbon")
    website_id = fields.Many2one(related="product_tmpl_id.website_id", readonly=False)

    product_template_image_ids = fields.One2many(
        related="product_tmpl_id.product_template_image_ids", readonly=False
    )
    variant_image_ids = fields.Many2many(
        string="Variant Extra Images",
        comodel_name="product.image",
        relation="product_product_image_rel",
        compute="_compute_variant_image_ids",
        store=True,
    )

    website_url = fields.Char(
        string="Website URL",
        help="The full URL to access the document through the website.",
        compute="_compute_product_website_url",
    )

    # === COMPUTE METHODS ===#

    @api.depends("product_template_image_ids")
    def _compute_variant_image_ids(self):
        for product in self:
            variant_ptavs = product.product_template_attribute_value_ids
            product.variant_image_ids = product.product_template_image_ids.filtered(
                lambda image: (
                    image.has_attribute_value
                    and all(
                        variant_ptavs.filtered(lambda v: v.attribute_line_id == attribute_line)
                        & image.attribute_value_ids.filtered(
                            lambda v: v.attribute_line_id == attribute_line
                        )
                        for attribute_line in image.attribute_value_ids.attribute_line_id
                    )
                )
            )

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

    # === CRUD METHODS === #

    @api.model_create_multi
    def create(self, vals_list):
        products = super().create(vals_list)

        for product, vals in zip(products, vals_list):
            if vals.get("image_1920"):
                product._set_extra_image_from_main_image(vals.get("image_1920"))
        return products

    def write(self, vals):
        if "active" in vals and not vals["active"]:
            # unlink draft lines containing the archived product
            self.env["sale.order.line"].sudo().search([
                ("state", "=", "draft"),
                ("product_id", "in", self.ids),
                ("order_id", "any", [("website_id", "!=", False)]),
            ]).unlink()

        res = super().write(vals)

        if vals.get("image_variant_1920") and not self.env.context.get("from_extra_image"):
            for product in self:
                product._set_extra_image_from_main_image(
                    vals.get("image_variant_1920"), skip_update=True
                )

        if "image_variant_1920" in vals and not vals["image_variant_1920"]:
            images_to_unlink = self.env["product.image"]
            for product in self:
                images_to_unlink |= product.variant_image_ids.sorted("sequence")[:1]

            if images_to_unlink:
                images_to_unlink.unlink()

        return res

    @api.ondelete(at_uninstall=False)
    def _unlink_variant_images(self):
        images = self.env["product.image"]
        for product in self:
            images |= product.variant_image_ids.filtered(
                lambda image: (
                    image.attribute_value_ids == product.product_template_attribute_value_ids
                )
            )
        images.unlink()

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
        """Return the images to display in the website product carousel.

        The images are returned in their configured display order.

        If the variant has its own main image, the applicable extra images
        are displayed in their configured order. Otherwise, the first
        applicable extra image is displayed first. If there are no extra
        images, the variant itself is returned.
        """
        self.ensure_one()
        extra_images = self._get_all_extra_images_to_display()
        if not self.image_variant_1920:
            first_image = self.product_template_image_ids.sorted("sequence")[:1]
            extra_images = first_image + (extra_images - first_image)
        return extra_images or self

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
        return self.product_tmpl_id._website_show_quick_add(self)

    def _is_add_to_cart_allowed(self) -> bool:
        """Determine whether the current user is permitted to buy the product."""
        self.ensure_one()
        if self._is_donation():
            return True

        website = self.env.website
        return (
            website.has_ecommerce_access()
            and self._is_purchasable()
            and self._is_published()
            and (
                not website.prevent_sale
                or not website._prevent_product_sale(self, not self._get_contextual_price())
            )
        )

    def _is_published(self) -> bool:
        return self.product_tmpl_id._is_published()

    def _is_purchasable(self) -> bool:
        """Determine whether the given product can be sold through the eCommerce shop."""
        self.ensure_one()
        return self.product_tmpl_id._is_purchasable(product=self)

    @api.onchange("public_categ_ids")
    def _onchange_public_categ_ids(self):
        if self.public_categ_ids:
            self.website_published = True
        else:
            self.website_published = False

    def _prepare_jsonld_vals(self, **kwargs):
        """JSON-LD payload describing the variant as a https://schema.org/Product."""
        self.ensure_one()

        website = self.env.website or self.env["website"].browse(self.env.context.get("host_id"))
        base_url = website.get_base_url()
        product_price = kwargs.get("precomputed_price")
        if product_price is None:
            product_price = request.pricelist._get_product_price(
                self, quantity=1, currency=website.currency_id
            )
        # Use sudo to access cross-company taxes.
        price = self._apply_taxes_to_price(product_price, website.currency_id, website=website)

        offer = {"@type": "Offer", "price": price, "priceCurrency": website.currency_id.name}
        if self.is_product_variant and self.is_storable:
            offer["availability"] = (
                "https://schema.org/OutOfStock"
                if self._is_sold_out()
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
        if self.default_code:
            vals["sku"] = self.default_code
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
            for extra_image in self._get_all_extra_images_to_display()
            if extra_image.image_128  # only images, no video urls
        ]

    def _get_all_extra_images_to_display(self):
        """Return the extra images to display for this variant on the website.

        The returned images are ordered with variant-specific images first,
        followed by template-level images that are not associated with any
        attribute values.

        Note: self.ensure_one()

        :rtype: product.image
        :return: Recordset of extra images to display.
        """
        self.ensure_one()
        return self.variant_image_ids.sorted("sequence") + self.product_template_image_ids.sorted(
            "sequence"
        ).filtered(lambda image: not image.has_attribute_value)

    def _set_extra_image_from_main_image(self, image, skip_update=False):
        """Create or update the extra image corresponding to the product's main image.

        If `skip_update` is enabled and the product already has an extra image, that
        image is updated. Otherwise, a new extra image is created.

        Note: self.ensure_one()

        :param image: Binary image data for the extra image.
        :param bool skip_update: Whether to skip synchronizing the product's main
            image while creating or updating the extra image.
        """
        self.ensure_one()

        if self.variant_image_ids and skip_update:
            self.variant_image_ids.sorted("sequence")[0].with_context(
                skip_update_main_image=True
            ).image_1920 = image
            return

        ProductImage = self.env["product.image"].sudo()
        if skip_update:
            ProductImage = ProductImage.with_context(skip_update_main_image=True)

        ProductImage.create({
            "name": self.display_name,
            "image_1920": image,
            "product_tmpl_id": self.product_tmpl_id.id,
            "attribute_value_ids": [Command.set(self.product_template_attribute_value_ids.ids)],
            "sequence": self.variant_image_ids.sorted("sequence")[:1].sequence - 1,
        })

    def _set_main_image_from_extra_images(self):
        """Set the products's main image from its extra images."""
        for product in self:
            if product.variant_image_ids:
                first_product_image = product.variant_image_ids.sorted("sequence")[0]
                if first_product_image.video_url:
                    raise ValidationError(
                        product.env._("You can't use a video as the product's main image.")
                    )
                if product.image_variant_1920.content == first_product_image.image_1920.content:
                    continue
                product.with_context(
                    from_extra_image=True
                ).image_variant_1920 = first_product_image.image_1920
            else:
                product.image_variant_1920 = False

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

    def _has_stock_notification(self, partner, website):
        self.ensure_one()
        return bool(
            self
            .env["product.stock.notification"]
            .sudo()
            .search_count(
                [
                    ("product_id", "=", self.id),
                    ("website_id", "=", website.id),
                    ("partner_id", "=", partner.id),
                ],
                limit=1,
            )
        )

    def _get_free_qty(self, **_kwargs):
        """Return the free quantity of the product.

        :param dict _kwargs: Optional data used in overrides of this method
        :return: available quantity
        :rtype: float
        """
        return self.qty_available - self.outgoing_qty

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
        """Send back-in-stock emails to all subscribers whose product is now available.

        For each (product, website) group that is no longer sold
        out, sends one email per subscriber using the website-specific template, then
        deletes the notification record.

        The sender address is resolved in order:
        - company partner email
        - website salesperson email
        - company email_formatted, which includes the mail alias domain catchall
        """
        email_template = self.env.ref(
            "website_sale.email_template_back_in_stock", raise_if_not_found=False
        )
        if not email_template:
            return
        grouped_notifications = self.env["product.stock.notification"]._read_group(
            [], groupby=["product_id", "website_id"], aggregates=["id:recordset"]
        )
        notifications_to_send = [
            notification
            for product, website, notification in grouped_notifications
            if not product
            .with_company(website.company_id)
            .with_context(website_id=website.id)
            ._is_sold_out()
        ]
        self.env["ir.cron"]._commit_progress(remaining=len(notifications_to_send))
        for notification in notifications_to_send:
            website = notification.website_id
            partner = notification.partner_id
            product = notification.product_id
            sender_email = (
                website.company_id.partner_id.email_formatted
                or website.salesperson_id.email_formatted
                or website.company_id.email_formatted
            )
            email_template.with_user(website.salesperson_id).sudo().with_context(
                customer_name=partner.name, lang=partner.lang, website_id=website.id
            ).send_mail(
                product.id,
                force_send=True,
                email_values={"email_to": partner.email_formatted, "email_from": sender_email},
            )

            notification.sudo().unlink()
            self.env["ir.cron"]._commit_progress(1)

    def _split_standard_from_custom_attributes(self):
        self.ensure_one()
        return self.product_template_attribute_value_ids._split_standard_from_custom_attributes()

    def _apply_taxes_to_price(self, *args, **kwargs):
        self.ensure_one()
        return self.product_tmpl_id._apply_taxes_to_price(*args, product=self, **kwargs)

    def _can_add_to_stock_notifications(self):
        """Return whether the product is eligible for stock notifications.

        Note: `self.ensure_one()`

        :return: True if the product is active, saleable, and published on the website
        :rtype: bool
        """
        self.ensure_one()
        return self.active and self.sale_ok and self.website_published

    def _mail_get_operation_for_mail_message_operation(self, message_operation):
        if (
            message_operation == "create"
            and not self.env.user._is_internal()
            and not self.env["website"].is_view_active("website_sale.product_comment")
        ):
            return [(Domain.TRUE, "write")]
        return super()._mail_get_operation_for_mail_message_operation(message_operation)

    def _can_return_content(self, field_name=None, access_token=None):
        """Override of `BaseModel` to allow showing donation product image to public users."""
        if (
            field_name in ["image_%s" % size for size in [1920, 1024, 512, 256, 128]]
            and self._is_donation()
        ):
            return True
        return super()._can_return_content(field_name, access_token)
