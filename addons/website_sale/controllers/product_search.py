# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.fields import Domain
from odoo.http import Controller, request, route


class ProductSearch(Controller):
    @route(
        "/shop/product_search/filters", type="jsonrpc", auth="public", website=True, readonly=True
    )
    def product_search_filters(self):
        website_domain = request.env.website.website_domain()

        tags_domain = Domain.AND([Domain("visible_to_customers", "=", True), website_domain])
        tags = request.env["product.tag"].search_read(tags_domain, ["id", "name"], order="name")

        categories_domain = Domain.AND([
            Domain("parent_id", "=", False),
            Domain("not_in_shop", "=", False),
            website_domain,
        ])
        categories = request.env["product.public.category"].search_read(
            categories_domain, ["id", "name"], order="sequence, name"
        )

        ribbons = request.env["product.ribbon"].search_read(
            [("assign", "=", "manual")], ["id", "name"], order="sequence, id"
        )

        attributes = request.env["product.attribute"].search(
            [("visibility", "=", "visible")], order="sequence, id"
        )
        attributes_data = [
            {
                "id": attribute.id,
                "name": attribute.name,
                "display_type": attribute.display_type,
                "values": [
                    {
                        "id": value.id,
                        "name": value.name,
                        "html_color": value.html_color,
                        "has_image": bool(value.image),
                    }
                    for value in attribute.value_ids
                ],
            }
            for attribute in attributes
            if attribute.value_ids
        ]

        return {
            "tags": tags,
            "categories": categories,
            "ribbons": ribbons,
            "attributes": attributes_data,
        }
