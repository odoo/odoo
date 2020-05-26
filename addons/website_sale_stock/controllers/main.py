# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.exceptions import UserError
from odoo.http import request
from odoo.tools import ustr
from odoo.tools.pycompat import izip

class WebsiteSale(WebsiteSale):

    def get_attribute_value_ids(self, product):
        res = super(WebsiteSale, self).get_attribute_value_ids(product)
        variant_ids = [r[0] for r in res]
        # recordsets conserve the order
        for r, variant in izip(res, request.env['product.product'].sudo().browse(variant_ids)):
            r.extend([{
                'virtual_available': variant.virtual_available,
                'product_type': variant.type,
                'inventory_availability': variant.inventory_availability,
                'available_threshold': variant.available_threshold,
                'custom_message': variant.custom_message,
                'product_template': variant.product_tmpl_id.id,
                'cart_qty': variant.cart_qty,
                'uom_name': variant.uom_id.name,
            }])

        return res

    @http.route()
    def payment_transaction(self, **kwargs):
        """ Payment transaction override to double check cart quantities before
        placing the order
        """
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.product_id.type == 'product' and line.product_id.inventory_availability in ['always', 'threshold']:
                cart_qty = sum(order.order_line.filtered(lambda p: p.product_id.id == line.product_id.id).mapped('product_uom_qty'))
                avl_qty = line.product_id.virtual_available
                if cart_qty > avl_qty:
                    values.append(_('You ask for %s products but only %s is available') % (cart_qty, avl_qty if avl_qty > 0 else 0))
        if values:
            raise UserError('. '.join(values) + '.')
        return super(WebsiteSale, self).payment_transaction(**kwargs)
