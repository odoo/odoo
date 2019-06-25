# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.controllers.portal import PortalAccount
from odoo.http import request
from odoo.osv import expression


class PortalAccount(PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super(PortalAccount, self)._invoice_get_page_view_values(invoice, access_token, **kwargs)
        acquirers_sudo = request.env['payment.acquirer'].sudo()._get_available_acquirers(partner=invoice.partner_id, company=invoice.company_id)
        payment_vals = acquirers_sudo._get_payment_form_values(invoice.partner_id, amount=invoice.residual, currency=invoice.currency_id)
        values.update(payment_vals)
        # if the current user is connected we set partner_id to his partner otherwise we set it as the invoice partner
        # we do this to force the creation of payment tokens to the correct partner and avoid token linked to the public user
        is_public_user = request.env.user._is_public()
        values['partner_id'] = invoice.partner_id if is_public_user else request.env.user.partner_id,
        return values
