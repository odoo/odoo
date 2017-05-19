# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class OgoneController(http.Controller):
    _accept_url = '/payment/ogone/test/accept'
    _decline_url = '/payment/ogone/test/decline'
    _exception_url = '/payment/ogone/test/exception'
    _cancel_url = '/payment/ogone/test/cancel'

    @http.route([
        '/payment/ogone/accept', '/payment/ogone/test/accept',
        '/payment/ogone/decline', '/payment/ogone/test/decline',
        '/payment/ogone/exception', '/payment/ogone/test/exception',
        '/payment/ogone/cancel', '/payment/ogone/test/cancel',
    ], type='http', auth='none')
    def ogone_form_feedback(self, **post):
        """ Ogone contacts using GET, at least for accept """
        _logger.info('Ogone: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'ogone')
        return werkzeug.utils.redirect(post.pop('return_url', '/'))

    @http.route(['/payment/ogone/s2s/create_json'], type='json', auth='public', csrf=False)
    def ogone_s2s_create_json(self, **kwargs):
        new_id = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        return new_id.id

    @http.route(['/payment/ogone/s2s/create'], type='http', auth='public', methods=["POST"], csrf=False)
    def ogone_s2s_create(self, **post):
        error = ''
        acq = request.env['payment.acquirer'].browse(int(post.get('acquirer_id')))
        try:
            acq.s2s_process(post)
        except Exception as e:
            # synthax error: 'CHECK ERROR: |Not a valid date\n\n50001111: None'
            error = str(e).splitlines()[0].split('|')[-1] or ''
        return werkzeug.utils.redirect(post.get('return_url', '/') + (error and '#error=%s' % werkzeug.url_quote(error) or ''))

    @http.route(['/payment/ogone/s2s/feedback'], auth='none', csrf=False)
    def feedback(self, **kwargs):
        try:
            tx = request.env['payment.transaction'].sudo()._ogone_form_get_tx_from_data(kwargs)
            tx._ogone_s2s_validate()
        except ValidationError:
            return 'ko'
        return 'ok'
