# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import route
from odoo.addons.account.controllers.portal import CustomerPortal


class CustomerPortalExternalTax(CustomerPortal):
    @route()
    def portal_my_invoice_detail(self, *args, **kw):
        response = super().portal_my_invoice_detail(*args, **kw)
        if 'invoice' not in response.qcontext:
            return response

        invoice = response.qcontext['invoice']
        invoice.with_company(invoice.company_id)._get_and_set_external_taxes_on_eligible_records()

        return response
