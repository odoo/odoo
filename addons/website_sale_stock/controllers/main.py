# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.addons.website_sale.controllers.main import WebsiteSale

from odoo import http,_
from odoo.http import request
from odoo.exceptions import ValidationError


class WebsiteSaleStock(WebsiteSale):
    @http.route()
    def payment_transaction(self, *args, **kwargs):
        """ Payment transaction override to double check cart quantities before
        placing the order
        """
        order = request.website.sale_get_order()
        values = []
        for line in order.order_line:
            if line.product_id.type == 'product' and line.product_id.inventory_availability in ['always', 'threshold']:
                cart_qty = sum(order.order_line.filtered(lambda p: p.product_id.id == line.product_id.id).mapped('product_uom_qty'))
                avl_qty = line.product_id.with_context(warehouse=order.warehouse_id.id).virtual_available
                if cart_qty > avl_qty:
                    values.append(_('You ask for %s products but only %s is available') % (cart_qty, avl_qty if avl_qty > 0 else 0))
        if values:
            raise ValidationError('. '.join(values) + '.')
        return super(WebsiteSaleStock, self).payment_transaction(*args, **kwargs)
