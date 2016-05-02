# -*- coding: utf-8 -*-
import datetime

from openerp import http
from openerp.exceptions import AccessError
from openerp.http import request

from openerp.addons.website_portal.controllers.main import website_account


class website_account(website_account):

    @http.route()
    def account(self):
        """ Add sales documents to main account page """
        response = super(website_account, self).account()
        partner = request.env.user.partner_id

        SaleOrder = request.env['sale.order']
        Invoice = request.env['account.invoice']
        quotation_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ])
        order_count = SaleOrder.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done'])
        ])
        invoice_count = Invoice.search_count([
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['open', 'paid', 'cancelled'])
        ])

        response.qcontext.update({
            'quotation_count': quotation_count,
            'order_count': order_count,
            'invoice_count': invoice_count,
        })
        return response

    #
    # Quotations and Sale Orders
    #

    @http.route(['/my/quotes', '/my/quotes/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_quotes(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sent', 'cancel'])
        ]

        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin), ('create_date', '<', date_end)]

        # count for pager
        quotation_count = SaleOrder.search_count(domain)
        # make pager
        pager = request.website.pager(
            url="/my/quotes",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=quotation_count,
            page=page,
            step=self._items_per_page
        )
        # search the count to display, according to the pager data
        quotations = SaleOrder.search(domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'quotations': quotations,
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/quotes',
        })
        return request.website.render("website_portal_sale.portal_my_quotations", values)

    @http.route(['/my/orders', '/my/orders/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_orders(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        SaleOrder = request.env['sale.order']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['sale', 'done'])
        ]
        archive_groups = self._get_archive_groups('sale.order', domain)
        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin), ('create_date', '<', date_end)]

        # count for pager
        order_count = SaleOrder.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/orders",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=order_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        orders = SaleOrder.search(domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'date': date_begin,
            'orders': orders,
            'page_name': 'order',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/orders',
        })
        return request.website.render("website_portal_sale.portal_my_orders", values)

    @http.route(['/my/orders/<int:order>'], type='http', auth="user", website=True)
    def orders_followup(self, order=None, **kw):
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

    #
    # Invoices
    #

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        AccountInvoice = request.env['account.invoice']

        domain = [
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['open', 'paid', 'cancelled'])
        ]
        archive_groups = self._get_archive_groups('account.invoice', domain)
        if date_begin and date_end:
            domain += [('create_date', '>=', date_begin), ('create_date', '<', date_end)]

        # count for pager
        invoice_count = AccountInvoice.search_count(domain)
        # pager
        pager = request.website.pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        invoices = AccountInvoice.search(domain, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/invoices',
        })
        return request.website.render("website_portal_sale.portal_my_invoices", values)
