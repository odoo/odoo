# Part of Odoo. See LICENSE file for full copyright and licensing details

from odoo.http import Controller, request, route


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
