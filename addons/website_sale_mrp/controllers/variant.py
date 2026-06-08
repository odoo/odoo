# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request, route

from odoo.addons.website_sale.controllers.variant import WebsiteSaleVariantController


class WebsiteSaleMrpVariantController(WebsiteSaleVariantController):

    @route()
    def get_combination_info_website(
        self, product_template_id, product_id, combination, add_qty, uom_id=None, **kwargs
    ):
        combination_info = super().get_combination_info_website(
            product_template_id, product_id, combination, add_qty, uom_id=uom_id, **kwargs
        )

        if (
            (so := request.cart)
            and combination_info['product_id']
            and combination_info.get('is_storable')
            and not combination_info.get('allow_out_of_stock_order')
        ):
            combination_info['unavailable_kit_qty'] = so._get_unavailable_quantity_from_kits(
                request.env['product.product'].browse(combination_info['product_id']),
            )

        return combination_info
