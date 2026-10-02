# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import Controller, route


class ProductSearch(Controller):
    @route(
        "/shop/product_search/filters", type="jsonrpc", auth="public", website=True, readonly=True
    )
    def product_search_filters(self, tags=False, categories=False, ribbons=False, attributes=False):
        website_domain = self.env.website.website_domain()
        filter_data = {}

        if tags:
            tags_domain = Domain("visible_to_customers", "=", True) & website_domain
            filter_data["tags"] = self.env["product.tag"].search_read(tags_domain, ["name"])

        if categories:
            categories_domain = (
                Domain([("parent_id", "=", False), ("not_in_shop", "=", False)]) & website_domain
            )
            filter_data["categories"] = self.env["product.public.category"].search_read(
                categories_domain, ["name"]
            )

        if ribbons:
            filter_data["ribbons"] = self.env["product.ribbon"].search_read(
                [("assign", "=", "manual")], ["name"]
            )

        if attributes:
            attributes_domain = Domain([("visibility", "=", "visible"), ("value_ids", "!=", False)])
            # `attributes` is either True to get all the attributes (the editor),
            # or a list of ids to get these attributes with their values
            if attributes is True:
                filter_data["attributes"] = self.env["product.attribute"].search_read(
                    attributes_domain, ["name"]
                )
            else:
                filter_data["attributes"] = self.env["product.attribute"].web_search_read(
                    attributes_domain & Domain("id", "in", attributes),
                    {
                        "name": {},
                        "display_type": {},
                        "value_ids": {"fields": {"name": {}, "html_color": {}, "image": {}}},
                    },
                )["records"]

        return filter_data
