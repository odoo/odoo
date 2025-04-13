from odoo import http
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class CinetPayController(http.Controller):

    @http.route('/payment/cinetpay/ipn', type='json', auth='public', methods=['POST'], csrf=False)
    def cinetpay_ipn(self, **kwargs):
        _logger.info("IPN reçu de CinetPay : %s", kwargs)

        tx_reference = kwargs.get('transaction_id')
        if not tx_reference:
            _logger.error("Pas de transaction_id dans l'IPN CinetPay.")
            return "Missing transaction_id"

        tx = request.env['payment.transaction'].sudo().search([('reference', '=', tx_reference)], limit=1)
        if not tx:
            _logger.error("Transaction non trouvée pour référence %s", tx_reference)
            return "Transaction not found"

        try:
            tx._handle_notification_data('cinetpay', kwargs)
            return "OK"
        except Exception as e:
            _logger.exception("Erreur de traitement de l'IPN : %s", e)
            return "Error"
