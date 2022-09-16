# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.http import request

from odoo.addons.account.controllers import portal
from odoo.addons.payment.controllers.portal import PaymentPortal
from odoo.addons.portal.controllers.portal import _build_url_w_params


class PortalAccount(portal.PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super()._invoice_get_page_view_values(invoice, access_token, **kwargs)
        logged_in = not request.env.user._is_public()
        # We set partner_id to the partner id of the current user if logged in, otherwise we set it
        # to the invoice partner id. We do this to ensure that payment tokens are assigned to the
        # correct partner and to avoid linking tokens to the public user.
        partner_sudo = request.env.user.partner_id if logged_in else invoice.partner_id
        invoice_company = invoice.company_id or request.env.company

        providers_sudo = request.env['payment.provider'].sudo()._get_compatible_providers(
            invoice_company.id,
            partner_sudo.id,
            invoice.amount_total,
            currency_id=invoice.currency_id.id
        )  # In sudo mode to read the fields of providers and partner (if not logged in)
        tokens = request.env['payment.token'].search(
            [('provider_id', 'in', providers_sudo.ids), ('partner_id', '=', partner_sudo.id)]
        )  # Tokens are cleared at the end if the user is not logged in

        # Make sure that the partner's company matches the invoice's company.
        if not PaymentPortal._can_partner_pay_in_company(partner_sudo, invoice_company):
            providers_sudo = request.env['payment.provider'].sudo()
            tokens = request.env['payment.token']

        fees_by_provider = {
            pro_sudo: pro_sudo._compute_fees(
                invoice.amount_total, invoice.currency_id, invoice.partner_id.country_id
            ) for pro_sudo in providers_sudo.filtered('fees_active')
        }
        values.update({
            'providers': providers_sudo,
            'tokens': tokens,
            'fees_by_provider': fees_by_provider,
            'show_tokenize_input': PaymentPortal._compute_show_tokenize_input_mapping(
                providers_sudo, logged_in=logged_in
            ),
            'amount': invoice.amount_residual,
            'currency': invoice.currency_id,
            'partner_id': partner_sudo.id,
            'access_token': access_token,
            'transaction_route': f'/invoice/transaction/{invoice.id}/',
            'landing_route': _build_url_w_params(invoice.access_url, {'access_token': access_token})
        })
        if not logged_in:
            # Don't display payment tokens of the invoice partner if the user is not logged in, but
            # inform that logging in will make them available.
            values.update({
                'existing_token': bool(tokens),
                'tokens': request.env['payment.token'],
            })
        return values
