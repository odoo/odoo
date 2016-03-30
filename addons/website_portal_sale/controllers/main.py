# -*- coding: utf-8 -*-
import datetime

from openerp import http
from openerp.exceptions import AccessError
from openerp.http import request

from openerp.addons.website_portal.controllers.main import website_account


class website_account(website_account):
    @http.route(['/my/home'], type='http', auth="user", website=True)
    def account(self, **kw):
        """ Add sales documents to main account page """
        response = super(website_account, self).account()
        partner = request.env.user.partner_id

        res_sale_order = request.env['sale.order']
        res_invoices = request.env['account.invoice']
        quotations = res_sale_order.search([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ])
        orders = res_sale_order.search([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done'])
        ])
        invoices = res_invoices.search([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['open', 'paid', 'cancelled'])
        ])

        response.qcontext.update({
            'date': datetime.date.today().strftime('%Y-%m-%d'),
            'quotations': quotations,
            'orders': orders,
            'invoices': invoices,
        })
        return response

    @http.route(['/my/orders/<int:order>'], type='http', auth="user", website=True)
    def orders_followup(self, order=None):
        order = request.env['sale.order'].browse([order])
        try:
            order.check_access_rights('read')
            order.check_access_rule('read')
        except AccessError:
                return request.website.render("website.403")
        order_invoice_lines = {il.product_id.id: il.invoice_id for il in order.invoice_ids.mapped('invoice_line_ids')}
        return request.website.render("website_portal_sale.orders_followup", {
            'order': order.sudo(),
            'order_invoice_lines': order_invoice_lines,
        })
