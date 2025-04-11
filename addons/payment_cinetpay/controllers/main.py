import logging
from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)

class CinetpayController(http.Controller):
    _return_url = '/payment/cinetpay/return'
    _notify_url = '/payment/cinetpay/notify'

    @http.route(_return_url, type='http', auth='public', methods=['GET'])
    def cinetpay_return(self, **data):
        _logger.info('Return data from Cinetpay: %s', data)
        return request.redirect('/payment/status')

    @http.route(_notify_url, type='json', auth='public', csrf=False)
    def cinetpay_notify(self, **data):
        _logger.info('Notify data from Cinetpay: %s', data)
        tx = request.env['payment.transaction'].sudo().search([('reference', '=', data.get('transaction_id'))])
        if tx:
            tx._handle_notification_data('cinetpay', data)
        return 'OK'
