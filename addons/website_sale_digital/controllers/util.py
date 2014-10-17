#!/usr/bin/env python
from openerp.addons.web.http import request


def get_digital_purchases(uid):
    user = request.env['res.users'].browse(uid)
    partner = user.partner_id

    # Get paid invoices
    purchases = request.env['account.invoice.line'].sudo().search_read(
        domain=[('invoice_id.state', '=', 'paid'), ('invoice_id.partner_id', '=', partner.id), ('product_id.product_tmpl_id.digital_content', '=', True)],
        fields=['product_id'],
    )

    # I only want product_ids, but search_read insists in giving me a list of
    # (product_id: <id>, name: <product code> <template_name> <attributes>)
    return map(lambda x: x['product_id'][0], purchases)
