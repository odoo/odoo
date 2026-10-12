import logging

from odoo import http

from odoo.addons.payment_adyen.controllers.main import AdyenController

_logger = logging.getLogger(__name__)


class PosPaymentAdyenController(AdyenController):

    @http.route()
    def adyen_webhook(self, **post):
        if post.get('eventCode') in ['CAPTURE', 'AUTHORISATION_ADJUSTMENT'] and post.get('success') != 'true':
            _logger.warning('%s for transaction_id %s failed', post.get('eventCode'), post.get('originalReference'))
        return super().adyen_webhook(**post)
