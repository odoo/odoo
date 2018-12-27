# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.http import request

class WebsiteSale(WebsiteSale):
    def _get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist, **kw):
        res = super(WebsiteSale, self)._get_combination_info(product_template_id, product_id, combination, add_qty, pricelist, **kw)

        if res['product_id']:
            product = request.env['product.product'].sudo().browse(res['product_id'])
            res.update({
                'virtual_available': product.virtual_available,
                'product_type': product.type,
                'inventory_availability': product.inventory_availability,
                'available_threshold': product.available_threshold,
                'custom_message': product.custom_message,
                'product_template': product.product_tmpl_id.id,
                'cart_qty': product.cart_qty,
                'uom_name': product.uom_id.name,
            })
        else:
            product_template = request.env['product.template'].sudo().browse(product_template_id)
            res.update({
                'virtual_available': 0,
                'product_type': product_template.type,
                'inventory_availability': product_template.inventory_availability,
                'available_threshold': product_template.available_threshold,
                'custom_message': product_template.custom_message,
                'product_template': product_template.id,
                'cart_qty': 0
            })

        return res
