# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


class PortalAccount(CustomerPortal):
    
    def _get_account_invoice_domain(self):
        partner = request.env.user.partner_id
        domain = [
            ('type', 'in', ['out_invoice', 'out_refund']),
            ('message_partner_ids', 'child_of', [partner.commercial_partner_id.id]),
            ('state', 'in', ['open', 'paid', 'cancel'])
        ]
        return domain

    def _prepare_portal_layout_values(self):
        values = super(PortalAccount, self)._prepare_portal_layout_values()
        invoice_count = request.env['account.invoice'].search_count(self._get_account_invoice_domain())
        values['invoice_count'] = invoice_count
        return values

    # ------------------------------------------------------------
    # My Invoices
    # ------------------------------------------------------------

    def _invoice_check_access(self, invoice_id, access_token=None):
        invoice = request.env['account.invoice'].browse([invoice_id])
        invoice_sudo = invoice.sudo()
        try:
            invoice.check_access_rights('read')
            invoice.check_access_rule('read')
        except AccessError:
            if not access_token or not consteq(invoice_sudo.access_token, access_token):
                raise
        return invoice_sudo

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = {
            'page_name': 'invoice',
            'invoice': invoice,
        }
        if access_token:
            values['no_breadcrumbs'] = True
            values['access_token'] = access_token

        if kwargs.get('error'):
            values['error'] = kwargs['error']
        if kwargs.get('warning'):
            values['warning'] = kwargs['warning']
        if kwargs.get('success'):
            values['success'] = kwargs['success']

        return values

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, **kw):
        values = self._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        AccountInvoice = request.env['account.invoice']

        domain = self._get_account_invoice_domain()

        searchbar_sortings = {
            'date': {'label': _('Invoice Date'), 'order': 'date_invoice desc'},
            'duedate': {'label': _('Due Date'), 'order': 'date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        archive_groups = self._get_archive_groups('account.invoice', domain)
        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        # count for pager
        invoice_count = AccountInvoice.search_count(domain)
        # pager
        pager = portal_pager(
            url="/my/invoices",
            url_args={'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
            total=invoice_count,
            page=page,
            step=self._items_per_page
        )
        # content according to pager and archive selected
        invoices = AccountInvoice.search(domain, order=order, limit=self._items_per_page, offset=pager['offset'])
        values.update({
            'date': date_begin,
            'invoices': invoices,
            'page_name': 'invoice',
            'pager': pager,
            'archive_groups': archive_groups,
            'default_url': '/my/invoices',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
        })
        return request.render("account.portal_my_invoices", values)

    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, **kw):
        try:
            invoice_sudo = self._invoice_check_access(invoice_id, access_token)
        except AccessError:
            return request.redirect('/my')

        values = self._invoice_get_page_view_values(invoice_sudo, access_token, **kw)
        return request.render("account.portal_invoice_page", values)

    @http.route(['/my/invoices/pdf/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_report(self, invoice_id, access_token=None, **kw):
        try:
            invoice_sudo = self._invoice_check_access(invoice_id, access_token)
        except AccessError:
            return request.redirect('/my')

        # print report as sudo, since it require access to taxes, payment term, ... and portal
        # does not have those access rights.
        pdf = request.env.ref('account.account_invoices').sudo().render_qweb_pdf([invoice_sudo.id])[0]
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)

    # ------------------------------------------------------------
    # My Home
    # ------------------------------------------------------------

    def details_form_validate(self, data):
        error, error_message = super(PortalAccount, self).details_form_validate(data)
        # prevent VAT/name change if invoices exist
        partner = request.env['res.users'].browse(request.uid).partner_id
        invoices = request.env['account.invoice'].sudo().search_count([('partner_id', '=', partner.id), ('state', 'not in', ['draft', 'cancel'])])
        if invoices:
            if 'vat' in data and (data['vat'] or False) != (partner.vat or False):
                error['vat'] = 'error'
                error_message.append(_('Changing VAT number is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))
            if 'name' in data and (data['name'] or False) != (partner.name or False):
                error['name'] = 'error'
                error_message.append(_('Changing your name is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))
        return error, error_message
