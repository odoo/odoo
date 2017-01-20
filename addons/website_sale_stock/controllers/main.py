# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale


class WebsiteSale(WebsiteSale):

    def get_attribute_value_ids(self, product):
        res = super(WebsiteSale, self).get_attribute_value_ids(product)
        result = []
        for variant in product.sudo().product_variant_ids:
            for r in res:
                if r[0] == variant.id:
                    r.extend([{
                        'virtual_available': variant.virtual_available,
                        'product_type': str(variant.type),
                        'inventory_availability': str(variant.inventory_availability),
                        'available_threshold': variant.available_threshold,
                        'custom_message': str(variant.custom_message),
                        'product_template': variant.product_tmpl_id.id,
                        'cart_qty': variant.cart_qty
                    }])
                    result.append(r)
        return result
