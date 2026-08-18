# Part of Odoo. See LICENSE file for full copyright and licensing details.

from werkzeug.exceptions import Forbidden, NotFound

from odoo.http import route

from odoo.addons.payment.controllers import portal as payment_portal


class Editor(payment_portal.PaymentPortal):
    """Routes backing the website builder's "Customize" panel for the shop, product, and
    wishlist pages.
    """

    @route(["/shop/config/product"], type="jsonrpc", auth="user")
    def change_product_config(self, product_id, **options):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        model = options.get("model", "product.template")

        product = self.env[model].browse(product_id)
        if "sequence" in options:
            sequence = options["sequence"]
            if sequence == "top":
                product.set_sequence_top()
            elif sequence == "bottom":
                product.set_sequence_bottom()
            elif sequence == "up":
                product.set_sequence_up()
            elif sequence == "down":
                product.set_sequence_down()
        if {"x", "y"} <= options.keys():
            product.write({"website_size_x": options["x"], "website_size_y": options["y"]})
        if {"tag_field", "tag_ids"} <= options.keys():
            product.write({options["tag_field"]: options["tag_ids"] or False})

    @route(["/shop/config/attribute"], type="jsonrpc", auth="user")
    def change_attribute_config(self, attribute_id, **options):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        attribute = self.env["product.attribute"].browse(attribute_id)
        if "display_type" in options:
            attribute.write({"display_type": options["display_type"]})
            self.env.transaction.invalidate_ormcache("templates")

    @route(["/shop/config/website"], type="jsonrpc", auth="user", website=True)
    def _change_website_config(self, **options):
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise NotFound

        # Restrict options we can write to.
        writable_fields = {
            "shop_page_container",
            "shop_ppg",
            "shop_ppr",
            "shop_default_sort",
            "shop_gap",
            "shop_opt_products_design_classes",
            "product_page_container",
            "product_page_image_layout",
            "product_page_image_width",
            "product_page_grid_columns",
            "product_page_image_spacing",
            "product_page_image_ratio",
            "product_page_image_ratio_mobile",
            "product_page_cols_order",
            "product_page_image_roundness",
            "product_page_cta_design",
            # wishlist
            "wishlist_opt_products_design_classes",
            "wishlist_grid_columns",
            "wishlist_mobile_columns",
            "wishlist_gap",
        }
        # Default ppg to 1.
        if "ppg" in options and not options["ppg"]:
            options["ppg"] = 1
        if "product_page_grid_columns" in options:
            options["product_page_grid_columns"] = int(options["product_page_grid_columns"])

        # Checkout Extra Step
        if "extra_step" in options:
            extra_step_view = self.env.website.viewref("website_sale.extra_info")
            extra_step = self.env.website._get_checkout_step("/shop/extra_info")
            extra_step_view.active = extra_step.is_published = options.get("extra_step") == "true"

        if "extra_step_category_ids" in options:
            category_ids = options["extra_step_category_ids"]
            self.env.website.extra_step_category_ids = (
                self.env["product.public.category"].browse(category_ids).exists()
            )

        write_vals = {k: v for k, v in options.items() if k in writable_fields}
        if write_vals:
            self.env.website.write(write_vals)

    @route(["/shop/config/category"], type="jsonrpc", auth="user")
    def _change_category_config(self, category_id, **options):
        category = self.env["product.public.category"].browse(int(category_id))
        if not category.exists():
            raise NotFound

        # Restrict options we can write to.
        targeted_options = {
            "show_category_title",
            "show_category_description",
            "align_category_content",
        }
        modified_options = {
            option: value for option, value in options.items() if option in targeted_options
        }
        if modified_options:
            category.write(modified_options)

    @route(["/shop/config/tag"], type="jsonrpc", auth="user")
    def _change_tag_config(self, tag_id, **options):
        tag = self.env["product.tag"].browse(int(tag_id))
        if not tag.exists():
            raise NotFound
        if "color" in options:
            tag.color = options["color"]
        if "image" in options:
            image_data = self.env["ir.attachment"].browse(options["image"]).raw
            tag.image = image_data

    @route("/snippets/category/set_image", type="jsonrpc", auth="user")
    def set_category_image(self, category_id, attachment_id):
        """
        Set the cover image on the category.

        :param int category_id: ID of the category to set the cover image.
        :param int attachment_id: ID of the attachment containing the image data.
        :raise Forbidden: If the user does not have website editing access
        """
        if not self.env.user.has_group("website.group_website_restricted_editor"):
            raise Forbidden
        category = self.env["product.public.category"].browse(category_id).exists()
        if category:
            image_data = self.env["ir.attachment"].browse(attachment_id).raw
            category.cover_image = image_data
