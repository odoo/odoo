# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PayUMoneyController(http.Controller):
    _return_url = '/payment/payumoney/return'

    @http.route(_return_url, type='http', auth='public', methods=['GET', 'POST'], csrf=False, save_session=False)
    def payumoney_return(self, **data):
        """ PayUmoney.
        The session cookie created by Odoo has not the attribute SameSite. Most of browsers will force this attribute
        with the value 'Lax'. After the payment, PayUMoney will perform a POST request on this route. For all these reasons,
        the cookie won't be added to the request. As a result, if we want to save the session, the server will create
        a new session cookie. Therefore, the previous session and all related information will be lost, so it will lead
        to undesirable behaviors. This is the reason why `save_session=False` is needed.
        """
        _logger.info("entering handle_feedback_data with data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_feedback_data('payumoney', data)
        return request.redirect('/payment/status')
