# -*- coding: utf-8 -*-
from openerp import http
from openerp.http import request

class CardReader(http.Controller):
    @http.route('/pos/send_payment_transaction', type='json', auth='user')
    def payment_handler(self, **k):
        return request.env['card_reader.mercury_transaction'].do_payment(k, request.session.uid)

    @http.route('/pos/send_reversal', type='json', auth='user')
    def reversal_handler(self, **k):
        return request.env['card_reader.mercury_transaction'].do_reversal(k, request.session.uid, False)

    @http.route('/pos/send_voidsale', type='json', auth='user')
    def voidsale_handler(self, **k):
        return request.env['card_reader.mercury_transaction'].do_reversal(k, request.session.uid, True)
