# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.controllers.portal import PortalAccount
from odoo.http import request


class PortalAccount(PortalAccount):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super(PortalAccount, self)._invoice_get_page_view_values(invoice, access_token, **kwargs)
        payment_inputs = request.env['payment.acquirer']._get_available_payment_input(company=invoice.company_id)
        # if not connected (using public user), the method _get_available_payment_input will return public user tokens
        is_public_user = request.env.ref('base.public_user') == request.env.user
        if is_public_user:
            # we should not display payment tokens owned by the public user
            payment_inputs.pop('pms', None)
            token_count = request.env['payment.token'].sudo().search_count([('acquirer_id.company_id', '=', invoice.company_id.id),
                                                                      ('partner_id', '=', invoice.partner_id.id),
                                                                    ])
            values['existing_token'] = token_count > 0
        values.update(payment_inputs)
        # if the current user is connected we set partner_id to his partner otherwise we set it as the invoice partner
        # we do this to force the creation of payment tokens to the correct partner and avoid token linked to the public user
        values['partner_id'] = invoice.partner_id if is_public_user else request.env.user.partner_id,
        return values
