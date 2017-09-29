# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo.addons.account.controllers.portal import CustomerPortal
from odoo.http import request


class CustomerPortal(CustomerPortal):

    def _invoice_get_page_view_values(self, invoice, access_token, **kwargs):
        values = super(CustomerPortal, self)._invoice_get_page_view_values(invoice, access_token, **kwargs)
        values.update(request.env['payment.acquirer']._get_available_payment_input(invoice.partner_id, invoice.company_id))
        return values
