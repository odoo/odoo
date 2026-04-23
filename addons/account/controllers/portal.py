# Part of Odoo. See LICENSE file for full copyright and licensing details.

from collections import OrderedDict

from odoo import _, fields, http
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Domain
from odoo.http import request
from odoo.tools import email_normalize, email_normalize_all
from odoo.tools.misc import verify_hash_signed

from odoo.addons.account.controllers.download_docs import _build_zip_from_data, _get_headers
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.addons.portal.controllers.portal import pager as portal_pager


class PortalAccount(CustomerPortal):

    def _prepare_portal_counter_values(self, counter):
        if counter == 'overdue_invoice_count':
            return 'account.move', self._get_overdue_invoices_domain(), 'read'
        if counter == 'invoice_count':
            return 'account.move', self._get_invoices_domain('out'), 'read'
        if counter == 'bill_count':
            return 'account.move', self._get_invoices_domain('in'), 'read'
        return super()._prepare_portal_counter_values(counter)

    # ------------------------------------------------------------
    # My Invoices
    # ------------------------------------------------------------

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
        return Domain('state', 'not in', ('cancel', 'draft')) & Domain('move_type', 'in', move_type)

    def _get_overdue_invoices_domain(self, partner_id=None):
        return [
            ('state', 'not in', ('cancel', 'draft')),
            ('move_type', 'in', ('out_invoice', 'out_receipt')),
            ('payment_state', 'not in', ('in_payment', 'paid', 'reversed', 'blocked', 'invoicing_legacy')),
            ('invoice_date_due', '<', fields.Date.context_today(request.env.user)),
            ('partner_id', '=', partner_id or request.env.user.partner_id.id),
        ]

    def _get_account_searchbar_sortings(self):
        return {
            'date': {'label': _('Date'), 'order': 'invoice_date desc'},
            'duedate': {'label': _('Due Date'), 'order': 'invoice_date_due desc'},
            'name': {'label': _('Reference'), 'order': 'name desc'},
            'state': {'label': _('Status'), 'order': 'payment_state'},
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

        domain = Domain(domain or Domain.TRUE) & self._get_invoices_domain()

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
                "url_args": {'date_begin': date_begin, 'date_end': date_end, 'sortby': sortby, 'filterby': filterby},
                "total": AccountInvoice.search_count(domain) if AccountInvoice.has_access('read') else 0,
                "page": page,
                "step": self._items_per_page,
            },
            'default_url': url,
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': OrderedDict(sorted(searchbar_filters.items())),
            'filterby': filterby,
            'overdue_invoice_count': request.env['account.move'].search_count(self._get_overdue_invoices_domain())
                if request.env['account.move'].has_access('read') else 0,
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
                raw = bytes(docs_data[0]['content'])
                headers = self._get_http_headers(invoice_sudo, report_type, raw, download)
                return request.make_response(raw, list(headers.items()))
            else:
                filename = invoice_sudo._get_invoice_report_filename(extension='zip')
                zip_content = _build_zip_from_data(docs_data)
                headers = _get_headers(filename, 'zip', zip_content)
                return request.make_response(zip_content, headers)

        elif report_type in ('html', 'pdf', 'text'):
            has_generated_invoice = bool(invoice_sudo.invoice_pdf_report_id)
            request.update_context(proforma_invoice=not has_generated_invoice)
            # If the partner's language is RTL, set the context language to match, ensuring the report shows the correct text direction.
            partner_lang = invoice_sudo.partner_id.lang
            if partner_lang and request.env['res.lang']._get_data(code=partner_lang).direction == 'rtl':
                request.update_context(lang=partner_lang)
            # Use the template set on the related partner if there is.
            # This is not perfect as the invoice can still have been computed with another template, but it's a slight fix/imp for stable.
            pdf_report_name = invoice_sudo.partner_id.invoice_template_pdf_report_id.report_name or 'account.account_invoices'
            return self._show_report(model=invoice_sudo, report_type=report_type, report_ref=pdf_report_name, download=download)

        values = self._invoice_get_page_view_values(invoice_sudo, access_token, **kw)
        return request.render("account.portal_invoice_page", values)

    @http.route(['/my/journal/<int:journal_id>/unsubscribe'], type='http', auth="public", methods=['GET', 'POST'], website=True)
    def portal_my_journal_unsubscribe(self, journal_id, **kw):
        def _render(ctx, status=200):
            return request.render('account.portal_my_journal_mail_notifications', ctx, status=status)

        if access_token := kw.get('token'):
            try:
                token_data = verify_hash_signed(request.env(su=True), request.env['account.journal']._get_journal_notification_unsubscribe_scope(), access_token)
            except ValueError:
                return _render({'error': _('Invalid token')}, 403)
            if not token_data or token_data.get('journal_id') != journal_id:
                return _render({'error': _('Invalid token')}, 403)
            journal = request.env['account.journal'].sudo().browse(journal_id)
        else:
            # Legacy link for authenticated user trying to unsubscribe (needs access rights on journal)
            journal = request.env['account.journal'].browse(journal_id)

        if access_token:
            email_to_unsubscribe = email_normalize(token_data.get('email_to_unsubscribe'), strict=False)
        else:
            emails = email_normalize_all(journal.incoming_einvoice_notification_email or '')
            if len(emails) != 1:
                return _render({'error': _('Deprecated link')}, 410)
            email_to_unsubscribe = emails[0]

        if not journal.exists() or not email_to_unsubscribe:
            return _render({'error': _('Already unsubscribed')}, 404)

        if not journal.has_access('write'):
            return _render({'error': _('Invalid token')}, 403)

        journal = journal.with_company(journal.sudo().company_id.id)

        all_recipients = email_normalize_all(journal.incoming_einvoice_notification_email or '')
        email_found = any(r == email_to_unsubscribe for r in all_recipients)

        if not email_found:
            return _render({'error': _('Already unsubscribed')}, 404)

        if request.httprequest.method == 'POST':
            journal._unsubscribe_invoice_notification_email(email_to_unsubscribe)
            return _render({'journal': journal, 'email': email_to_unsubscribe, 'completed': True})

        return _render({'journal': journal, 'email': email_to_unsubscribe})
    # ------------------------------------------------------------
    # My Home
    # ------------------------------------------------------------

    def _prepare_my_account_rendering_values(self, *args, **kwargs):
        rendering_values = super()._prepare_my_account_rendering_values(*args, **kwargs)
        rendering_values.update({
            'invoice_sending_methods': {'email': _("by Email")},
            'invoice_edi_formats': dict(request.env['res.partner']._fields['invoice_edi_format']._description_selection(request.env)),
        })
        return rendering_values

    # ------------------------------------------------------------
    # Address form - additional identifiers
    # ------------------------------------------------------------

    def _get_checkout_additional_identifiers_metadata(self, country):
        """Return additional identifiers for a country."""
        if not country:
            return {}
        partner = request.env['res.partner'].new({'country_id': country.id})
        metadata = partner.available_additional_identifiers_metadata
        return {
            key: {
                'label': entry.get('label') or key,
                'placeholder': entry.get('placeholder') or '',
                'help': entry.get('help') or '',
            }
            for key, entry in sorted(metadata.items(), key=lambda item: item[1].get('sequence', 100))
        }

    def _prepare_address_form_values(self, partner_sudo, *args, **kwargs):
        rendering_values = super()._prepare_address_form_values(partner_sudo, *args, **kwargs)
        if rendering_values['is_used_as_billing']:
            metadata = self._get_checkout_additional_identifiers_metadata(rendering_values['country'])
            current_partner = partner_sudo or rendering_values['current_partner']
            rendering_values.update({
                'additional_identifiers_metadata': metadata,
                'partner_additional_identifiers': current_partner.additional_identifiers or {},
            })
        return rendering_values

    @http.route()
    def portal_address_country_info(self, country, address_type, **kw):
        res = super().portal_address_country_info(country, address_type, **kw)
        res['additional_identifiers_metadata'] = self._get_checkout_additional_identifiers_metadata(country)
        return res

    def _validate_address_values(self, address_values, *args, **kwargs):
        invalid_fields, missing_fields, error_messages = super()._validate_address_values(
            address_values, *args, **kwargs
        )
        additional_identifiers = address_values.get('additional_identifiers') or {}
        ResPartner = request.env['res.partner']
        if address_values.get('vat'):
            individual_keys = [key for key in additional_identifiers if ResPartner._is_individual_identifier(key)]
            if individual_keys:
                invalid_fields.update(individual_keys)
                error_messages.append(request.env._(
                    "An individual identifier cannot be combined with a VAT number."
                ))
        return invalid_fields, missing_fields, error_messages
