#!/usr/bin/env python
from openerp.addons.web.http import request

def get_digital_purchases(uid, confirmed=True):
    user = request.env['res.users'].browse(uid)
    partner = user.partner_id
    sale_orders = request.env['sale.order.line'].sudo()
    state = [('state', '=', 'confirmed')] if confirmed else []
    fields = ['product_id']

    purchases = sale_orders.search_read(
        domain=[('order_id.partner_id', '=', partner.id), ('product_id.product_tmpl_id.digital_content', '=', True)] + state,
        fields=fields,
    )

    # Hack for public user last session
    if 'sale_last_order_id' in request.session:
        last_purchase = sale_orders.search_read(
            domain=[('order_id', '=', request.session['sale_last_order_id']), ('product_id.product_tmpl_id.digital_content', '=', True)] + state,
            fields=fields,
        )
        purchases = purchases + last_purchase

    return purchases