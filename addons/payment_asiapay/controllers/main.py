import logging
import pprint

from odoo import _, http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

class AsiaPayController(http.Controller):
    _return_url = "/payment/asiapay/return"
    _notify_url = "/payment/asiapay/notify"

    @http.route(_return_url, type="http", auth="public", methods=['GET'])
    def asiapay_return(self, **data):
        return request.redirect('/payment/status')

    @http.route(_notify_url, type="http", auth="public", methods=['POST'], csrf=False)
    def asiapay_notify(self, **post):
        _logger.info("received AsiaPay notification data:\n%s", pprint.pformat(post))
        self._asiapay_validate_notification(**post)
        request.env['payment.transaction'].sudo()._handle_feedback_data('asiapay', post)
        return 'success'

    def _asiapay_validate_notification(self, **post):
        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_feedback_data(
            'asiapay', post
        )
        if not tx_sudo:
            raise ValidationError(
                "AsiaPay: " + _(
                    "Received notification data with unknown reference:\n%s", pprint.pformat(post)
                )
            )
