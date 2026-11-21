from odoo import http
from odoo.fields import Domain
from odoo.http import request

from odoo.addons.account.controllers.portal import PortalAccount


class L10nPtPortalAccount(PortalAccount):

    def _l10n_pt_unissued_invoices_domain(self):
        # A PT invoice reaches its customer once it is issued (printed, sent or previewed), never before:
        # browsing the portal must not issue it.
        return (
            Domain('country_code', '=', 'PT')
            & Domain('move_type', 'in', ('out_invoice', 'out_refund', 'out_receipt'))
            & Domain('l10n_pt_document_number', '=', False)
        )

    def _get_invoices_domain(self, m_type=None):
        # EXTENDS account
        return super()._get_invoices_domain(m_type) & ~self._l10n_pt_unissued_invoices_domain()

    def _get_overdue_invoices_domain(self, partner_id=None):
        # EXTENDS account
        # Overdue invoices are counted on /my, and listed and paid at once on /my/invoices/overdue (account_payment).
        return Domain(super()._get_overdue_invoices_domain(partner_id)) & ~self._l10n_pt_unissued_invoices_domain()

    @http.route()
    def portal_my_invoice_detail(self, invoice_id, access_token=None, report_type=None, download=False, **kw):
        # EXTENDS account
        invoice_sudo = request.env['account.move'].sudo().browse(invoice_id).exists()
        if (
            invoice_sudo
            and invoice_sudo._l10n_pt_country_ok()
            and not invoice_sudo.l10n_pt_document_number
            and not request.env.user._is_internal()
        ):
            return request.redirect('/my')
        return super().portal_my_invoice_detail(invoice_id, access_token=access_token, report_type=report_type, download=download, **kw)
