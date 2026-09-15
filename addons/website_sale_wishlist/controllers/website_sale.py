from odoo.http import request, route

from odoo.addons.website_sale.controllers import main


class WebsiteSaleWishlist(main.WebsiteSale):
    def _prepare_additional_shop_context(self, values, **kwargs):
        vals = super()._prepare_additional_shop_context(values, **kwargs)
        vals["products_in_wishlist"] = (
            request.env["product.wishlist"].current().product_id.product_tmpl_id
        )
        return vals

    @route()
    def _change_website_config(self, **options):
        result = super()._change_website_config(**options)

        current_website = request.env["website"].get_current_website()

        wishlist_writable_fields = {
            "wishlist_opt_products_design_classes",
            "wishlist_grid_columns",
            "wishlist_mobile_columns",
            "wishlist_gap",
        }

        wishlist_write_vals = {
            k: v for k, v in options.items() if k in wishlist_writable_fields
        }
        if wishlist_write_vals:
            current_website.write(wishlist_write_vals)

        return result
