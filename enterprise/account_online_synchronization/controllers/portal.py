import json

from odoo import http
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal
from odoo.tools import format_amount, format_date
from odoo.exceptions import AccessError, MissingError, UserError


class OnlineSynchronizationPortal(CustomerPortal):

    @http.route(['/renew_consent/<int:journal_id>'], type='http', auth="public", website=True, sitemap=False)
    def portal_online_sync_renew_consent(self, journal_id, access_token=None, **kw):
        # Display a page to the user allowing to renew the consent for his bank sync.
        # Requires the same rights as the button in odoo.
        try:
            journal_sudo = self._document_check_access('account.journal', journal_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        values = self._prepare_portal_layout_values()
        # Ignore the route if the journal isn't one using bank sync.
        if not journal_sudo.account_online_account_id:
            raise request.not_found()

        balance = journal_sudo.account_online_account_id.balance
        if journal_sudo.account_online_account_id.currency_id:
            formatted_balance = format_amount(request.env, balance, journal_sudo.account_online_account_id.currency_id)
        else:
            formatted_balance = format_amount(request.env, balance, journal_sudo.currency_id or journal_sudo.company_id.currency_id)

        values.update({
            'bank': journal_sudo.bank_account_id.bank_name or journal_sudo.account_online_account_id.name,
            'bank_account': journal_sudo.bank_account_id.acc_number,
            'journal': journal_sudo.name,
            'latest_balance_formatted': formatted_balance,
            'latest_balance': balance,
            'latest_sync': format_date(request.env, journal_sudo.account_online_account_id.last_sync, date_format="MMM dd, YYYY"),
            'iframe_params': json.dumps(journal_sudo.action_extend_consent()),
        })
        return request.render("account_online_synchronization.portal_renew_consent", values)


    @http.route(['/renew_consent/<int:journal_id>/complete'], type='http', auth="public", methods=['POST'], website=True)
    def portal_online_sync_action_complete(self, journal_id, access_token=None, **kw):
        # Complete the consent renewal process
        try:
            journal_sudo = self._document_check_access('account.journal', journal_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        # Ignore the route if the journal isn't one using bank sync.
        if not journal_sudo.account_online_link_id:
            raise request.not_found()
        try:
            journal_sudo.account_online_link_id._update_connection_status()
            journal_sudo.manual_sync()
        except UserError:
            pass
        return request.make_response(json.dumps({'status': 'done'}))
