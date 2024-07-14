# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.addons.sale_subscription.controllers.portal import CustomerPortal


class CustomerPortalExternalTaxes(CustomerPortal):
    @http.route()
    def subscription(self, order_id, access_token=None, message='', message_class='', report_type=None, download=False, **kw):
        res = super().subscription(order_id, access_token=access_token, message=message, message_class=message_class,
                                   report_type=report_type, download=download, **kw)
        if 'sale_order' not in res.qcontext:
            return res

        order = res.qcontext['sale_order']
        order.with_company(order.company_id)._get_and_set_external_taxes_on_eligible_records()
        return res
