# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import Controller, route


class WebsiteSaleProductCategoriesController(Controller):
    @route(
        "/website_sale/snippet/product_categories",
        type="jsonrpc",
        auth="public",
        methods=["POST"],
        website=True,
        replica=True,
    )
    def get_categories_with_children(self, category_ids):
        """Return the given categories with their children, and the top-level categories.

        :param list category_ids: IDs of the categories to return.
        :return: The `categories` that can be displayed, by ID, as dicts with the `category` and
                 its `child_categories`; and the `top_category_ids`, by sequence.
        :rtype: dict
        """
        Category = self.env["product.public.category"]
        return {
            "categories": Category._prepare_product_categories_snippet_data([
                int(category_id) for category_id in category_ids
            ]),
            "top_category_ids": Category._get_product_categories_snippet_top_categories().ids,
        }
