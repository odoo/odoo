# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo.http import route
from odoo.addons.sale.controllers.portal import CustomerPortal


class CustomerPortalExternalTax(CustomerPortal):
    @route()
    def portal_order_page(self, *args, **kwargs):
        response = super().portal_order_page(*args, **kwargs)
        if 'sale_order' not in response.qcontext:
            return response

        # Update taxes before customers see their quotation. This also ensures that tax validation
        # works (e.g. customer has valid address, ...). Otherwise, errors will occur during quote
        # confirmation. Switch company so that property fields are read correctly.
        so = response.qcontext['sale_order']
        so.with_company(so.company_id)._get_and_set_external_taxes_on_eligible_records()

        return response
