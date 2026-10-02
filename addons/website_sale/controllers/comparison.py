# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, request, route


class ProductComparison(Controller):
    @route("/shop/compare", type="http", auth="public", website=True, sitemap=False)
    def product_compare(self, **post):
        product_ids = [int(i) for i in post.get("products", "").split(",") if i.isdigit()]
        if not product_ids:
            return request.redirect("/shop")

        # use search to check read access on each record/ids
        products = self.env["product.product"].search([("id", "in", product_ids)])
        return request.render(
            "website_sale.product_compare",
            {
                "products": products.with_context(display_default_code=False),
                "attrib_categories": products._prepare_categories_for_display(),
            },
        )

    @route("/shop/compare/get_product_data", type="jsonrpc", auth="public", website=True)
    def get_product_data(self, product_ids):
        products = self.env["product.product"].search([("id", "in", product_ids)])
        return [
            {
                "id": product.id,
                "display_name": product.with_context(display_default_code=False).display_name,
                "website_url": product.website_url,
                "image_url": product._get_image_1024_url(),
                **self._prepare_product_price_data(product._get_default_price_info()),
            }
            for product in products
        ]

    def _prepare_product_price_data(self, price_info):
        price_data = {
            "hide_price": price_info["hide_price"],
            "price": price_info.get("price", 0),
            "currency_id": (price_info.get("currency") or self.env.website.currency_id).id,
        }
        if list_price := price_info.get("list_price"):
            price_data["list_price"] = list_price
        return price_data
