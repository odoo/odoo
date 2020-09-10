# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.controllers import portal
from odoo.http import request


class PortalAccount(portal.PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super()._invoice_get_page_view_values(invoice, access_token, **kwargs)
        logged_in = not request.env.user._is_public()
        # If the current user is connected we set partner_id to his partner otherwise we set it as
        # the invoice partner. We do this to force the creation of payment tokens to the correct
        # partner and avoid linking tokens to the public user.
        partner_id = invoice.partner_id.id if not logged_in else request.env.user.partner_id.id
        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_compatible_acquirers(
            invoice.company_id.id or request.env.company.id,
            invoice.partner_id.id or request.env.user.partner_id.id,
        )  # In sudo mode to read on the partner fields if the user is not logged in
        tokens = request.env['payment.token'].search([
            ('acquirer_id', 'in', acquirers_sudo.ids),
            ('partner_id', '=', invoice.partner_id.id or request.env.user.partner_id.id),
        ])
        fees_by_acquirer = {
            acq_sudo: acq_sudo._compute_fees(
                invoice.amount_total, invoice.currency_id.id, invoice.company_id.country_id.id
            ) for acq_sudo in acquirers_sudo.filtered('fees_active')
        }
        values.update({
            'acquirers': acquirers_sudo,
            'tokens': tokens,
            'fees_by_acquirer': fees_by_acquirer,
            'show_tokenize_input': True,
            'currency': invoice.currency_id,
            'partner_id': partner_id,
            'access_token': access_token,
            'init_tx_route': f'/invoice/pay/{invoice.id}/',
        })
        if not logged_in:
            # we should not display payment tokens owned by the public user
            values.update({
                'existing_token': bool(tokens),
                'tokens': [],
            })
        return values
