import logging
from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.http import request
from odoo.exceptions import ValidationError
from odoo.addons.payment_qfpay import const

_logger = logging.getLogger(__name__)


class QFPayController(http.Controller):

    @http.route(const.RETURN_URL, type='http', auth='public', methods=['GET', 'POST'])
    def qfpay_return_from_checkout(self, **data):
        _logger.info("User returned from QFPay for transaction reference: %s", data.get('out_trade_no'))
        return request.redirect(const.STATUS_URL)

    @http.route(const.WEBHOOK_URL, type='http', auth='public', methods=['POST'], csrf=False)
    def qfpay_webhook(self, **data):
        _logger.info("QFPay webhook received with data:\n%s", data)
        reference = request.env['payment.transaction']._extract_reference('qfpay', data)

        if not reference:
            _logger.warning("QFPay: Missing reference in webhook data.")
            return "fail"

        tx_sudo = request.env['payment.transaction'].sudo().search([('reference', '=', reference)])
        if not tx_sudo:
            _logger.warning("QFPay Webhook validation failed: No transaction found for reference %s", reference)
            return "fail"

        try:
            self._verify_signature(data, tx_sudo)
            tx_sudo._process(data)
        except ValidationError as e:
            _logger.warning("QFPay Webhook validation failed: %s", e)
            return "fail"
        except Forbidden as e:
            _logger.warning("QFPay Webhook signature forbidden: %s", e)
            return "fail"
        except Exception:
            _logger.exception("Could not process the QFPay webhook notification.")
            return "fail"

        return "success"

    @staticmethod
    def _verify_signature(data, tx_sudo):
        """ Verify the signature. """
        received_sign = data.get('sign')
        if not received_sign:
            raise Forbidden("QFPay: Missing signature.")

        # Check signature using the provider logic connected to the transaction
        expected_sign = tx_sudo.provider_id._qfpay_generate_sign(data)
        if received_sign != expected_sign:
            raise Forbidden("QFPay: Invalid signature received from gateway.")
