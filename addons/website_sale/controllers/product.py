# Part of Odoo. See LICENSE file for full copyright and licensing details.

import itertools
from urllib.parse import urlsplit

from werkzeug.exceptions import NotFound

from odoo.exceptions import ValidationError
from odoo.fields import Command, Domain
from odoo.http import Controller, request, route
from odoo.tools import BinaryBytes

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
        # TODO: remove support for `attribute_values` query param in version 20 (or later).
        if not attribute_value_ids and (attribute_values := kwargs.get("attribute_values")):
            attribute_value_ids = {
                int(value_id)
                for value_id in attribute_values.split(",")
                if value_id and value_id.isdigit()
            }
            grouped_attributes_values = (
                self
                .env["product.attribute.value"]
                .browse(attribute_value_ids)
                .exists()
                .sorted()
                .grouped("attribute_id")
            )
            return {"redirect_url": self._get_url_with_attribute_values(grouped_attributes_values)}
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
                    or ptal.product_template_value_ids.filtered("ptav_active")[:1]
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
            "user_email": self.env.user.email
            or request.session.get("stock_notification_email", ""),
        }

    @route(
        [
            f"{SHOP_PATH}/<model('product.template'):product>",
            f"{SHOP_PATH}/<model('product.public.category'):category>/<model('product.template'):product>",
            f"{SHOP_PATH}/product/<model('product.template'):product>",
        ],
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
        # TODO: remove support for deprecated paths in version 20 (or later).
        path = product.website_url
        # Redirect to the correct product URL if needed. There are 2 potential reasons for
        # redirecting:
        # - A `/product` prefix was included in the path,
        # - A category slug was included in the path.
        if path != request.httprequest.path:
            query = request.httprequest.args.to_dict(flat=False)
            return request.redirect(product._get_product_url(query), code=301)

        product_values = self._prepare_product_values(
            # request context must be given to ensure context updates in overrides are correctly
            # forwarded to `_get_combination_info` call
            product.with_context(self.env.context),
            **kwargs,
        )
        if "redirect_url" in product_values:
            return request.redirect(product_values["redirect_url"], code=301)
        return request.render("website_sale.product", product_values)

    @route(
        '/shop/<model("product.template"):product_template>/document/<int:document_id>',
        type="http",
        auth="public",
        website=True,
        sitemap=False,
        readonly=True,
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

        if type == "image":  # Image case
            image_ids = self.env["ir.attachment"].browse(i["id"] for i in media)
            media_create_data = [
                Command.create({
                    "name": image.name,  # Images uploaded from url do not have any datas.
                    # This recovers them manually.
                    "image_1920": image.raw
                    or self.env["ir.qweb.field.image"].load_remote_url(image.url),
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
                })
            ]

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
        if (
            product_template.has_configurable_attributes
            and product_product
            and not all(
                pa.create_variant == "no_variant"
                for pa in product_template.attribute_line_ids.attribute_id
            )
        ):
            product_product.write({"product_variant_image_ids": media_create_data})
        else:
            product_template.write({"product_template_image_ids": media_create_data})

    @route(["/shop/product/clear-images"], type="jsonrpc", auth="user", website=True)
    def clear_product_images(self, product_product_id, product_template_id):
        """Unlink all images from the product."""
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

        if product_product and product_product.product_variant_image_ids:
            product_product.product_variant_image_ids.unlink()
        else:
            product_template.product_template_image_ids.unlink()

    @route(["/shop/product/resequence-image"], type="jsonrpc", auth="user", website=True)
    def resequence_product_image(self, image_res_model, image_res_id, move):
        """
        Move the product image in the given direction and update all images' sequence.

        :param str image_res_model: The model of the image. It can be 'product.template',
                                    'product.product', or 'product.image'.
        :param str image_res_id: The record ID of the image to move.
        :param str move: The direction of the move. It can be 'first', 'left', 'right', or 'last'.
        :raises NotFound: If the user does not have the required permissions, if the model of the
                          image is not allowed, or if the move direction is not allowed.
        :raise ValidationError: If the product is not found.
        :raise ValidationError: If the image to move is not found in the product images.
        :raise ValidationError: If a video is moved to the first position.
        :return: None
        """
        if (
            not self.env.user.has_group("website.group_website_restricted_editor")
            or image_res_model not in {"product.product", "product.template", "product.image"}
            or move not in {"first", "left", "right", "last"}
        ):
            raise NotFound

        image_res_id = int(image_res_id)
        image_to_resequence = self.env[image_res_model].browse(image_res_id)
        if image_res_model == "product.product":
            product = image_to_resequence
            product_template = product.product_tmpl_id
        elif image_res_model == "product.template":
            product_template = image_to_resequence
            product = product_template.product_variant_id
        else:
            product = image_to_resequence.product_variant_id
            product_template = product.product_tmpl_id or image_to_resequence.product_tmpl_id

        if not product and not product_template:
            raise ValidationError(self.env._("Product not found"))

        product_images = (product or product_template)._get_images()
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

        # If the main image has been reordered (i.e. it's no longer in first position), use the
        # image that's now in first position as main image instead.
        # Additional images are product.image records. The main image is a product.product or
        # product.template record.
        main_image_idx = next(
            idx for idx, image in enumerate(product_images) if image._name != "product.image"
        )
        if main_image_idx != 0:
            main_image = product_images[main_image_idx]
            additional_image = product_images[0]
            if additional_image.video_url:
                raise ValidationError(
                    self.env._("You can't use a video as the product's main image.")
                )
            # Swap records.
            product_images[main_image_idx], product_images[0] = additional_image, main_image
            # Swap image data. The contents are read eagerly before writing: the images are
            # stored in attachments, and writing the first field mutates its attachment, which
            # would invalidate the other value that is still lazily bound to its attachment.
            main_image_data = main_image.image_1920.content
            additional_image_data = additional_image.image_1920.content
            main_image.image_1920 = BinaryBytes(additional_image_data)
            additional_image.image_1920 = BinaryBytes(main_image_data)
            additional_image.name = main_image.name  # Update image name but not product name.

        # Resequence additional images according to the new ordering.
        for idx, product_image in enumerate(product_images):
            if product_image._name == "product.image":
                product_image.sequence = idx

    @route(
        ["/shop/product/is_add_to_cart_allowed"],
        type="jsonrpc",
        auth="public",
        website=True,
        readonly=True,
    )
    def is_add_to_cart_allowed(self, product_id, **_kwargs):
        product = self.env["product.product"].browse(product_id)
        # In sudo mode to check fields and conditions not accessible to the customer directly.
        return product.sudo()._is_add_to_cart_allowed()


class WebsiteSaleVariantController(Controller):
    @route(
        "/website_sale/get_combination_info",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        readonly=True,
    )
    def get_combination_info_website(
        self, product_template_id, product_id, combination, add_qty, uom_id=None, **_kwargs
    ):
        request.update_context(website_sale_product_page=True)
        product_template_id = product_template_id and int(product_template_id)
        product_id = product_id and int(product_id)
        add_qty = (add_qty and float(add_qty)) or 1.0

        product_template = self.env["product.template"].browse(product_template_id)

        combination_info = product_template._get_combination_info(
            combination=self.env["product.template.attribute.value"].browse(combination),
            product_id=product_id,
            add_qty=add_qty,
            uom_id=uom_id,
        )
        combination_info["currency_precision"] = combination_info["currency"].decimal_places

        for key in (
            # Only provided to ease server-side computations.
            "product_taxes",
            "taxes",
            "currency",
            "combination",
            # Only used in Google Merchant Center logic, not client-side.
            "discount_start_date",
            "discount_end_date",
        ):
            combination_info.pop(key)

        product = self.env["product.product"].browse(combination_info["product_id"])
        if product and product.id == product_id:
            combination_info["no_product_change"] = True
            return combination_info

        if self.env.website.product_page_image_width != "none" and not self.env.context.get(
            "website_sale_no_images", False
        ):
            product_or_template = product or product_template
            combination_info["display_image"] = bool(product_or_template.image_128)
            combination_info["carousel"] = self.env.website._render_template(
                "website_sale.shop_product_images",
                values={
                    "product": product_template,
                    "product_variant": product,
                    "website": self.env.website,
                },
            )

        if self.env.website.is_view_active("website_sale.documents"):
            combination_info["documents"] = self.env.website._render_template(
                "website_sale.documents",
                values={"product": product_template, "product_variant": product},
            )

        if self.env.website.is_view_active("website_sale.product_tags"):
            all_tags = product.all_product_tag_ids if product else product_template.product_tag_ids
            combination_info["product_tags"] = self.env.website._render_template(
                "website_sale.product_tags",
                values={"all_product_tags": all_tags.filtered("visible_to_customers")},
            )

        combination_info["packaging_selector"] = self.env["ir.ui.view"]._render_template(
            "website_sale.product_packaging_selector",
            values={
                "product": product_template,
                "product_variant": product,
                "combination_info": combination_info,
            },
        )

        return combination_info

    @route(
        "/website_sale/get_attribute_images",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        readonly=True,
    )
    def get_dynamic_attribute_images(self, product_template_id, combination, **_kwargs):
        product_template = self.env["product.template"].browse(int(product_template_id))
        return product_template._get_dynamic_attribute_images(
            self.env["product.template.attribute.value"].browse(combination).exists().ids,
            self.env.website.id,
        )

    @route("/sale/create_product_variant", type="jsonrpc", auth="public", methods=["POST"])
    def create_product_variant(
        self, product_template_id, product_template_attribute_value_ids, **_kwargs
    ):
        """Old product configurator logic, only used by frontend configurator, will be
        deprecated soon."""
        return (
            self
            .env["product.template"]
            .browse(int(product_template_id))
            .create_product_variant(product_template_attribute_value_ids)
        )
