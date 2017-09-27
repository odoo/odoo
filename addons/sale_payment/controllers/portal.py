# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.sale.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortal(CustomerPortal):

    def _order_get_page_view_values(self, order, access_token, **kwargs):
        values = super(CustomerPortal, self)._order_get_page_view_values(order, access_token, **kwargs)
        if values['portal_confirmation'] == 'pay':
            values.update(request.env['payment.acquirer']._get_available_payment_input(order.partner_id, order.company_id))
        return values
