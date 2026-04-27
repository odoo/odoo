# Part of Odoo. See LICENSE file for full copyright and licensing details.
from odoo import http
from odoo.addons.sale_subscription.controllers.portal import CustomerPortal


class CustomerPortalExternalTaxes(CustomerPortal):
    @http.route()
    def subscription(self, order_id, access_token=None, message='', report_type=None, download=False, **kw):
        order_sudo, _ = self._get_subscription(access_token, order_id)
        order_sudo.with_company(order_sudo.company_id)._get_and_set_external_taxes_on_eligible_records()
        return super().subscription(order_id, access_token=access_token, message=message, report_type=report_type, download=download, **kw)
