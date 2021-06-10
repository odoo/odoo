# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class BuckarooController(http.Controller):
    _return_url = '/payment/buckaroo/return'

    @http.route(_return_url, type='http', auth='public', methods=['POST'], csrf=False)
    def buckaroo_return_from_redirect(self, **data):
        """ Process the data returned by Buckaroo after redirection.

        :param dict data: The feedback data
        """
        _logger.info("received notification data:\n%s", pprint.pformat(data))
        request.env['payment.transaction'].sudo()._handle_feedback_data('buckaroo', data)
        return request.redirect('/payment/status')
