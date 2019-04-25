# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortal(CustomerPortal):

    def _order_get_page_view_values(self, order, access_token, **kwargs):
        values = super(CustomerPortal, self)._order_get_page_view_values(order, access_token, **kwargs)
        if values['portal_confirmation'] == 'pay':
            payment_inputs = request.env['payment.acquirer']._get_available_payment_input(order.partner_id, order.company_id)
            # if not connected (using public user), the method _get_available_payment_input will return public user tokens
            is_public_user = request.env.user._is_public()
            if is_public_user:
                # we should not display payment tokens owned by the public user
                payment_inputs.pop('pms', None)
                token_count = request.env['payment.token'].sudo().search_count([('acquirer_id.company_id', '=', order.company_id.id),
                                                                            ('partner_id', '=', order.partner_id.id),
                                                                        ])
                values['existing_token'] = token_count > 0
            values.update(payment_inputs)
            values['partner_id'] = order.partner_id if is_public_user else request.env.user.partner_id
        return values
