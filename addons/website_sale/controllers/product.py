# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from urllib.parse import urlsplit

from werkzeug.exceptions import NotFound

from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.http import request, route

from odoo.addons.payment.controllers import portal as payment_portal
from odoo.addons.website.controllers.main import QueryURL
from odoo.addons.website.models.ir_http import sitemap_qs2dom
from odoo.addons.website_sale.const import SHOP_PATH


class Product(payment_portal.PaymentPortal):
    def sitemap_products(env, _rule, qs):  # noqa: N805
        if env.website and env.website.ecommerce_access == "logged_in" and not qs:
            # Make sure urls are not listed in sitemap when restriction is active
            # and no autocomplete query string is provided
            return

        ProductTemplate = env["product.template"]
        dom = sitemap_qs2dom(qs, SHOP_PATH, ProductTemplate._rec_name)
        dom &= Domain(env.website.sale_product_domain())
        for product in ProductTemplate.with_context(prefetch_fields=False).search(dom):
            loc = product.website_url
            if not qs or qs.lower() in loc:
                yield {"loc": loc}

    @route(
        f"{SHOP_PATH}/<model('product.template'):product>",
        type="http",
        auth="public",
        website=True,
        sitemap=sitemap_products,
        # Return a 404 instead of a 403 error in case of an access error.
        handle_params_access_error=lambda e, **_kwargs: NotFound.code,  # noqa: ARG005
    )
    def product(self, product, pricelist=None, **kwargs):
        if not self.env.website.has_ecommerce_access():
            return request.redirect(f"/web/login?redirect={request.httprequest.path}")

        if pricelist is not None:
            try:
                pricelist_id = int(pricelist)
            except ValueError as ve:
                raise ValidationError(
                    self.env._("Wrong format: got `pricelist=%s`, expected an integer", pricelist)
                ) from ve
            if not self._apply_selectable_pricelist(pricelist_id):
                return request.redirect(SHOP_PATH)

        request.update_context(website_sale_product_page=True)

        search_term = kwargs.get("search")

        # Preselect the variant matching the search term, unless attribute values are already
        # given in the URL.
        if search_term and not self._get_attribute_value_params(kwargs):
            attribute_values = product._get_attribute_values_from_search_term(search_term)
            if attribute_values:
                redirect_url = self._get_url_with_attribute_values(
                    attribute_values.sorted().grouped("attribute_id")
                )
                return request.redirect(redirect_url, code=301)

        product_values = self._prepare_product_values(
            # request context must be given to ensure context updates in overrides are correctly
            # forwarded to `_get_combination_info` call
            product.with_context(self.env.context),
            **kwargs,
        )
        return request.render("website_sale.product", product_values)

    def _prepare_product_values(self, product, **kwargs):
        website = self.env.website
        category = product.public_categ_ids.filtered(
            lambda categ: categ.website_id.id in (website.id, False)
        )[:1]
        structured_data = product.with_context(
            shop_category_id=category.id if category else False
        )._render_jsonld(is_detail_page=True)
        keep = QueryURL(SHOP_PATH, **request.session.get("attribute_value_params", {}))

        attribute_value_params = self._get_attribute_value_params(kwargs)
        attribute_value_dict = self._get_attribute_value_dict(attribute_value_params)
        attribute_value_ids = set(itertools.chain.from_iterable(attribute_value_dict.values()))
        if attribute_value_ids:
            combination = product.attribute_line_ids.mapped(
                lambda ptal: (
                    (
                        ptal.product_template_value_ids.filtered(
                            lambda ptav: (
                                ptav.ptav_active
                                and ptav.product_attribute_value_id.id in attribute_value_ids
                            )
                        )[:1]
                    )
                    or (
                        ptal.product_template_value_ids.filtered(
                            lambda ptav: (
                                ptav.ptav_active and ptal.attribute_id.display_type != "multi"
                            )
                        )[:1]
                    )
                )
            )
            combination_info = product._get_combination_info(
                combination=combination.with_env(self.env)
            )
            attribute_value_images = product._get_dynamic_attribute_images(
                combination.ids, website.id
            )
        else:
            combination_info = product._get_combination_info()
            attribute_value_images = product._get_dynamic_attribute_images([], website.id)

        # Needed to trigger the recently viewed product rpc
        view_track = website.viewref("website_sale.product").track
        _, reset_filters = self._get_shop_filter_reset_params()

        return {
            "attribute_value_images": attribute_value_images,
            "categories": self.env["product.public.category"].search([("parent_id", "=", False)]),
            "category": category,
            "combination_info": combination_info,
            "has_available_uoms": len(product._get_available_uoms()) > 0,
            "keep": keep,
            "main_object": product,
            "product": product,
            "product_variant": self.env["product.product"].browse(combination_info["product_id"]),
            "view_track": view_track,
            "structured_data": structured_data,
            "shop_path": SHOP_PATH,
            "reset_filters": reset_filters,
            "user_email": self.env.user.email_normalized
            or request.session.get("stock_notification_email", ""),
        }

    @route(
        '/shop/<model("product.template"):product_template>/document/<int:document_id>',
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        replica=True,
    )
    def product_document(self, product_template, document_id):
        product_template.check_access("read")

        document = self.env["product.document"].browse(document_id).sudo().exists()
        if not document or not document.active:
            return request.redirect(SHOP_PATH)

        if document.attached_on_sale != "shown_on_product_page":
            return request.redirect(SHOP_PATH)

        if document.res_model == "product.template":
            if document.res_id != product_template.id:
                return request.redirect(SHOP_PATH)
        elif document.res_model == "product.product":
            if (
                request.env["product.product"].browse(document.res_id).product_tmpl_id.id
                != product_template.id
            ):
                return request.redirect(SHOP_PATH)
        else:
            return request.redirect(SHOP_PATH)

        return (
            self
            .env["ir.binary"]
            ._get_stream_from(document.ir_attachment_id)
            .get_response(as_attachment=True)
        )

    @route(["/shop/product/extra-media"], type="jsonrpc", auth="user", website=True)
    def add_product_media(
        self, media, type, product_product_id, product_template_id, combination_ids=None
    ):
        """
        Handle adding both images and videos to product variants or templates,
        links all of them to product.

        :param type: [...] can be either image or video
        :raises NotFound : If the user is not allowed to access Attachment model
        """
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        product_product = (
            self.env["product.product"].browse(int(product_product_id))
            if product_product_id
            else False
        )
        product_template = (
            self.env["product.template"].browse(int(product_template_id))
            if product_template_id
            else False
        )

        if product_product and not product_template:
            product_template = product_product.product_tmpl_id

        if not product_product and product_template and product_template.has_dynamic_attributes():
            combination = self.env["product.template.attribute.value"].browse(combination_ids)
            product_product = product_template._get_variant_for_combination(combination)
            if not product_product:
                product_product = product_template._create_product_variant(combination)

        is_variant_media = (
            product_template.has_configurable_attributes
            and product_product
            and not all(
                pa.create_variant == "no_variant"
                for pa in product_template.attribute_line_ids.attribute_id
            )
        )
        variant_media_values = {}
        if is_variant_media:
            variant_media_values["attribute_value_ids"] = [Command.set(combination_ids)]

        if type == "image":  # Image case
            image_ids = self.env["ir.attachment"].browse(i["id"] for i in media)
            media_create_data = [
                Command.create({
                    "name": image.name,  # Images uploaded from url do not have any datas.
                    # This recovers them manually.
                    "image_1920": image.raw
                    or self.env["ir.qweb.field.image"].load_remote_url(image.url),
                    **variant_media_values,
                })
                for image in image_ids
            ]
        elif type == "video":  # Video case
            video_data = media[0]
            url = urlsplit(video_data["video_url"])
            if not url.netloc:
                raise ValidationError(self.env._("Invalid video URL provided."))
            media_create_data = [
                Command.create({
                    "name": video_data.get("name", "Odoo Video"),
                    "video_url": video_data["video_url"],
                    "image_1920": video_data.get("image_1920"),
                    **variant_media_values,
                })
            ]

        product_template.write({"product_template_image_ids": media_create_data})

    @route(["/shop/product/resequence-image"], type="jsonrpc", auth="user", website=True)
    def resequence_product_image(self, image_res_id, move, product_variant_id):
        """
        Move the product image in the given direction and update all images' sequence.

        :param str image_res_id: The record ID of the image to move.
        :param str move: The direction of the move. It can be 'first', 'left', 'right', or 'last'.
        :param str product_variant_id: The ID of the product variant in whose context the image
                                       resequencing is performed
        :raises NotFound: If the user does not have the required permissions, if the model of the
                          image is not allowed, or if the move direction is not allowed.
        :raise ValidationError: If the product is not found.
        :raise ValidationError: If the image to move is not found in the product images.
        :return: None
        """
        if not self.env.user.has_group("website.group_website_restricted_editor") or move not in {
            "first",
            "left",
            "right",
            "last",
        }:
            raise NotFound

        image_res_id = int(image_res_id)
        image_to_resequence = self.env["product.image"].browse(image_res_id)

        product_template = image_to_resequence.product_tmpl_id
        product = self.env["product.product"].browse(int(product_variant_id))

        if not product and not product_template:
            raise ValidationError(self.env._("Product not found"))

        product_images = list((product or product_template)._get_images())

        if image_to_resequence not in product_images:
            raise ValidationError(self.env._("Invalid image"))

        image_idx = product_images.index(image_to_resequence)
        new_image_idx = 0
        if move == "left":
            new_image_idx = max(0, image_idx - 1)
        elif move == "right":
            new_image_idx = min(len(product_images) - 1, image_idx + 1)
        elif move == "last":
            new_image_idx = len(product_images) - 1

        # no-op resequences
        if new_image_idx == image_idx:
            return

        # Reorder images locally.
        product_images.insert(new_image_idx, product_images.pop(image_idx))

        # Resequence additional images according to the new ordering.
        for idx, product_image in enumerate(product_images):
            if product_image._name == "product.image":
                product_image.sequence = idx

    @route(
        ["/shop/product/is_add_to_cart_allowed"],
        type="jsonrpc",
        auth="public",
        website=True,
        replica=True,
    )
    def is_add_to_cart_allowed(self, product_id, **_kwargs):
        product = self.env["product.product"].browse(product_id)
        # In sudo mode to check fields and conditions not accessible to the customer directly.
        return product.sudo()._is_add_to_cart_allowed()
