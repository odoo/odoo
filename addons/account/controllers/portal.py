# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import fields, http, _
from odoo.osv import expression
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.addons.account.controllers.download_docs import _get_headers, _build_zip_from_data
from odoo.exceptions import AccessError, MissingError
from odoo.http import request


class PortalAccount(CustomerPortal):

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        if 'overdue_invoice_count' in counters:
            values['overdue_invoice_count'] = self._get_overdue_invoice_count()
        if 'invoice_count' in counters:
            invoice_count = request.env['account.move'].search_count(self._get_invoices_domain('out'), limit=1) \
                if request.env['account.move'].has_access('read') else 0
            values['invoice_count'] = invoice_count
        if 'bill_count' in counters:
            bill_count = request.env['account.move'].search_count(self._get_invoices_domain('in'), limit=1) \
                if request.env['account.move'].has_access('read') else 0
            values['bill_count'] = bill_count
        return values

    # ------------------------------------------------------------
    # My Invoices
    # ------------------------------------------------------------

    def _get_overdue_invoice_count(self):
        overdue_invoice_count = request.env['account.move'].search_count(self._get_overdue_invoices_domain()) \
            if request.env['account.move'].has_access('read') else 0
        return overdue_invoice_count

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        custom_amount = None
        if kwargs.get('amount'):
            custom_amount = float(kwargs['amount'])
        values = {
            'page_name': 'invoice',
            **invoice._get_invoice_portal_extra_values(custom_amount=custom_amount),
        }
        return self._get_page_view_values(invoice, access_token, values, 'my_invoices_history', False, **kwargs)

    def _get_invoices_domain(self, m_type=None):
        if m_type in ['in', 'out']:
            move_type = [m_type+move for move in ('_invoice', '_refund', '_receipt')]
        else:
            move_type = ('out_invoice', 'out_refund', 'in_invoice', 'in_refund', 'out_receipt', 'in_receipt')
        return [('state', 'not in', ('cancel', 'draft')), ('move_type', 'in', move_type)]

    def _get_overdue_invoices_domain(self, partner_id=None):
        return [
            ('state', 'not in', ('cancel', 'draft')),
            ('move_type', 'in', ('out_invoice', 'out_receipt')),
            ('payment_state', 'not in', ('in_payment', 'paid')),
            ('invoice_date_due', '<', fields.Date.today()),
            ('partner_id', '=', partner_id or request.env.user.partner_id.id),
        ]

    def _get_account_searchbar_sortings(self):
        return {
            'date': {'label': _('Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'state'},
        }

    def _get_account_searchbar_filters(self):
        return {
            'all': {'label': _('All'), 'domain': []},
            'overdue_invoices': {'label': _('Overdue invoices'), 'domain': self._get_overdue_invoices_domain()},
            'invoices': {'label': _('Invoices'), 'domain': [('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt'))]},
            'bills': {'label': _('Bills'), 'domain': [('move_type', 'in', ('in_invoice', 'in_refund', 'in_receipt'))]},
        }

    @http.route(['/my/invoices', '/my/invoices/page/<int:page>'], type='http', auth="user", website=True)
    def portal_my_invoices(self, page=1, date_begin=None, date_end=None, sortby=None, filterby=None, **kw):
        values = self._prepare_my_invoices_values(page, date_begin, date_end, sortby, filterby)

        # pager
        pager = portal_pager(**values['pager'])

        # content according to pager and archive selected
        invoices = values['invoices'](pager['offset'])
        request.session['my_invoices_history'] = [i['invoice'].id for i in invoices][:100]

        values.update({
            'invoices': invoices,
            'pager': pager,
        })
        return request.render("account.portal_my_invoices", values)

    def _prepare_my_invoices_values(self, page, date_begin, date_end, sortby, filterby, domain=None, url="/my/invoices"):
        values = self._prepare_portal_layout_values()
        AccountInvoice = request.env['account.move']

        domain = expression.AND([
            domain or [],
            self._get_invoices_domain(),
        ])

        searchbar_sortings = self._get_account_searchbar_sortings()
        # default sort by order
        if not sortby:
            sortby = 'date'
        order = searchbar_sortings[sortby]['order']

        searchbar_filters = self._get_account_searchbar_filters()
        # default filter by value
        if not filterby:
            filterby = 'all'
        domain += searchbar_filters[filterby]['domain']

        if date_begin and date_end:
            domain += [('create_date', '>', date_begin), ('create_date', '<=', date_end)]

        values.update({
            'date': date_begin,
            # content according to pager and archive selected
            # lambda function to get the invoices recordset when the pager will be defined in the main method of a route
            'invoices': lambda pager_offset: (
                [
                    invoice._get_invoice_portal_extra_values()
                    for invoice in AccountInvoice.search(
                        domain, order=order, limit=self._items_per_page, offset=pager_offset
                    )
                ]
                if AccountInvoice.has_access('read') else
                AccountInvoice
            ),
            'page_name': 'invoice',
            'pager': {  # vals to define the pager.
                "url": url,
                "url_args": {'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby},
                "total": AccountInvoice.search_count(domain) if AccountInvoice.has_access('read') else 0,
                "page": page,
                "step": self._items_per_page,
            },
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'overdue_invoice_count': self._get_overdue_invoice_count(),
        })
        return values

    @http.route(['/my/invoices/<int:invoice_id>'], type='http', auth="public", website=True)
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        try:
            invoice_sudo = self._document_check_access('account.move', invoice_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        if report_type == 'pdf' and download and invoice_sudo.state == 'posted':
            # Download the official attachment(s) or a Pro Forma invoice
            docs_data = invoice_sudo._get_invoice_legal_documents_all(allow_fallback=True)
            if len(docs_data) == 1:
                headers = self._get_http_headers(invoice_sudo, report_type, docs_data[0]['content'], download)
                return request.make_response(docs_data[0]['content'], list(headers.items()))
            else:
                filename = invoice_sudo._get_invoice_report_filename(extension='zip')
                zip_content = _build_zip_from_data(docs_data)
                headers = _get_headers(filename, 'zip', zip_content)
                return request.make_response(zip_content, headers)

        elif report_type in ('html', 'pdf', 'text'):
            has_generated_invoice = bool(invoice_sudo.invoice_pdf_report_id)
            request.update_context(proforma_invoice=not has_generated_invoice)
            # Use the template set on the related partner if there is.
            # This is not perfect as the invoice can still have been computed with another template, but it's a slight fix/imp for stable.
            pdf_report_name = invoice_sudo.partner_id.invoice_template_pdf_report_id.report_name or 'account.account_invoices'
            return self._show_report(model=invoice_sudo, report_type=report_type, report_ref=pdf_report_name, download=download)

        values = self._invoice_get_page_view_values(invoice_sudo, access_token, **kw)
        return request.render("account.portal_invoice_page", values)

    # ------------------------------------------------------------
    # My Home
    # ------------------------------------------------------------

    def details_form_validate(self, data, partner_creation=False):
        error, error_message = super(PortalAccount, self).details_form_validate(data)
        # prevent VAT/name change if invoices exist
        partner = request.env['res.users'].browse(request.uid).partner_id
        # Skip this test if we're creating a new partner as we won't ever block him from filling values.
        if not partner_creation and not partner.can_edit_vat():
            if 'vat' in data and (data['vat'] or False) != (partner.vat or False):
                error['vat'] = 'error'
                error_message.append(_('Changing VAT number is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))
            if 'name' in data and (data['name'] or False) != (partner.name or False):
                error['name'] = 'error'
                error_message.append(_('Changing your name is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))
            if 'company_name' in data and (data['company_name'] or False) != (partner.company_name or False):
                error['company_name'] = 'error'
                error_message.append(_('Changing your company name is not allowed once invoices have been issued for your account. Please contact us directly for this operation.'))
        return error, error_message

    def extra_details_form_validate(self, data, additional_required_fields, error, error_message):
        """ Ensure that all additional required fields have a value in the data """
        for field in additional_required_fields:
            if field.name not in data or not data[field.name]:
                error[field.name] = 'error'
                error_message.append(_('The field %s must be filled.', field.field_description.lower()))
        return error, error_message

    def _get_optional_fields(self):
        # EXTENDS 'portal
        optional_fields = super()._get_optional_fields()
        optional_fields.extend(('invoice_sending_method', 'invoice_edi_format'))
        return optional_fields

    def _prepare_portal_layout_values(self):
        # EXTENDS 'portal'
        portal_layout_values = super()._prepare_portal_layout_values()
        partner = request.env.user.partner_id
        portal_layout_values.update({
            'invoice_sending_methods': {'email': _('by Email')},
            'invoice_edi_formats': dict(partner._fields['invoice_edi_format'].selection),
        })
        return portal_layout_values
