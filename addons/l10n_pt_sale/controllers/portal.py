from odoo import http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request

from odoo.addons.sale.controllers import portal


class CustomerPortal(portal.CustomerPortal):

    @http.route()
    def portal_order_page(self, order_id, report_type=None, access_token=None, **kw):
        # EXTENDS sale
        # Only an internal user issues an order, by sending, sharing or printing it: never a customer's
        # request, which runs as the superuser and may come from any fetcher of the link. The
        # report of an order not issued yet is no document to hand out (Despacho 8632/2014 2.2.1): the
        # customer is sent back to its page.
        if report_type in ('html', 'pdf', 'text') and request.env.user.share:
            try:
                order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
            except (AccessError, MissingError):
                order_sudo = None
            if order_sudo and order_sudo._l10n_pt_is_unissued_document():
                return request.redirect(order_sudo.get_portal_url())
        return super().portal_order_page(order_id, report_type=report_type, access_token=access_token, **kw)

    @http.route()
    def portal_quote_decline(self, order_id, access_token=None, decline_message=None, **kwargs):
        # EXTENDS sale
        # An issued PT quotation is cancelled with a reason (Portaria 302/2016 4.3.4.3.3), which core's
        # decline does not give: the customer's message is that reason. Core cancels only a
        # quotation still to be signed, given a message.
        try:
            order_sudo = self._document_check_access('sale.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            order_sudo = None
        if (
            order_sudo
            and decline_message and decline_message.strip()
            and order_sudo._has_to_be_signed()
            and order_sudo._l10n_pt_issued_orders()
        ):
            order_sudo.l10n_pt_cancel_reason = decline_message.strip()
        return super().portal_quote_decline(order_id, access_token=access_token, decline_message=decline_message, **kwargs)

    @http.route()
    def portal_quote_accept(self, order_id, access_token=None, name=None, signature=None):
        # EXTENDS sale
        # An issued quotation the customer accepts stays as issued, and a new sales order is confirmed
        # from it: the customer lands on that sales order, confirmed.
        order_sudo = request.env['sale.order'].sudo().browse(order_id).exists()
        sales_orders_before = order_sudo.sales_order_ids
        result = super().portal_quote_accept(order_id, access_token=access_token, name=name, signature=signature)
        order_sudo.invalidate_recordset(['sales_order_ids'])
        if (sales_order := (order_sudo.sales_order_ids - sales_orders_before)[-1:]) and result.get('redirect_url'):
            result['redirect_url'] = sales_order.get_portal_url(query_string='&message=sign_ok')
        return result
