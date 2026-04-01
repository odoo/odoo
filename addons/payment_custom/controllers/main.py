# Part of Odoo. See LICENSE file for full copyright and licensing details.

import pprint

from odoo.http import Controller, request, route

from odoo.addons.payment.logging import get_payment_logger


_logger = get_payment_logger(__name__)


class CustomController(Controller):
    _process_url = '/payment/custom/process'

    @route(_process_url, type='http', auth='public', methods=['POST'], csrf=False)
    def custom_process_transaction(self, **post):
        _logger.info("Handling custom processing with data:\n%s", pprint.pformat(post))
        request.env['payment.transaction'].sudo()._process('custom', post)
        return request.redirect('/payment/status')
