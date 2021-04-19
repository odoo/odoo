# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import logging
import pprint
import requests
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class NeloController(http.Controller):
    _confirm_url = '/payment/nelo/confirm'
    _cancel_url = '/payment/nelo/cancel'

    # def _nelo_validate_data(self, **post):
    #     resp = post.get('trade_status')
    #     if resp:
    #         if resp in ['TRADE_FINISHED', 'TRADE_SUCCESS']:
    #             _logger.info('Nelo: validated data')
    #         elif resp == 'TRADE_CLOSED':
    #             _logger.warning('Nelo: payment refunded to user and closed the transaction')
    #         else:
    #             _logger.warning('Nelo: unrecognized nelo answer, received %s instead of TRADE_FINISHED/TRADE_SUCCESS and TRADE_CLOSED' % (post['trade_status']))
    #     if post.get('out_trade_no') and post.get('trade_no'):
    #         post['reference'] = request.env['payment.transaction'].sudo().search([('reference', '=', post['out_trade_no'])]).reference
    #         return request.env['payment.transaction'].sudo().form_feedback(post, 'nelo')
    #     return False

    @http.route('/payment/nelo/confirm', type='http', auth="public", methods=['GET', 'POST'])
    def nelo_return(self, **post):
        # self._nelo_validate_data(**post)
        return werkzeug.utils.redirect('/payment/process')

    @http.route('/payment/nelo/cancel', type='http', auth='public', methods=['GET', 'POST'], csrf=False)
    def nelo_notify(self, **post):
        _logger.info('Beginning Nelo cancel')
        return werkzeug.utils.redirect('/payment/process')
