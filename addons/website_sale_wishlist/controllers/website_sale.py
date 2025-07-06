# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers import main


class WebsiteSaleWishlist(main.WebsiteSale):

    def _get_additional_shop_values(self, values, **kwargs):
        """ Hook to update values used for rendering website_sale.products template """
        vals = super()._get_additional_shop_values(values, **kwargs)
        vals['products_in_wishlist'] = request.env['product.wishlist'].current().product_id.product_tmpl_id
        return vals

    @route()
    def _change_website_config(self, **options):
        result = super()._change_website_config(**options)

        current_website = request.env['website'].get_current_website()

        wishlist_writable_fields = {'wishlist_opt_products_design_classes'}

        wishlist_write_vals = {k: v for k, v in options.items() if k in wishlist_writable_fields}
        if wishlist_write_vals:
            current_website.write(wishlist_write_vals)

        return result
