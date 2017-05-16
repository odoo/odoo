# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import http, _
from odoo.exceptions import AccessError
from odoo.http import request

from odoo.addons.website_portal.controllers.main import website_account, get_records_pager


# class Payment(Controller):

#     @http.route(['/transaction_token/confirm'], type='json', auth="public", website=True)
#     def payment_transaction_token_confirm(self, tx_id, **kwargs):
#         tx = request.env['payment.transaction'].sudo().browse(int(tx_id))
#         if (tx and tx.payment_token_id and
#                 tx.partner_id == tx.sale_order_id.partner_id):
#             try:
#                 s2s_result = tx.s2s_do_transaction()
#                 valid_state = 'authorized' if tx.acquirer_id.auto_confirm == 'authorize' else 'done'
#                 if not s2s_result or tx.state != valid_state:
#                     return dict(success=False, error=_("Payment transaction failed (%s)") % tx.state_message)
#                 else:
#                     # Auto-confirm SO if necessary
#                     tx._confirm_so()
#                     return dict(success=True, url="/quote/%s/%s" % (tx.sale_order_id.id, tx.sale_order_id.access_token))
#             except Exception, e:
#                 _logger.warning(_("Payment transaction (%s) failed : <%s>") % (tx.id, str(e)))
#                 return dict(success=False, error=_("Payment transaction failed (Contact Administrator)"))
#         return dict(success=False, error='Tx missmatch')