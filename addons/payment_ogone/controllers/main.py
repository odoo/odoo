# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from openerp import http, SUPERUSER_ID
from openerp.http import request
from openerp.addons.payment.models.payment_acquirer import ValidationError

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
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        request.registry['payment.transaction'].form_feedback(cr, uid, post, 'ogone', context=context)
        return werkzeug.utils.redirect(post.pop('return_url', '/'))

    @http.route(['/payment/ogone/s2s/create_json'], type='json', auth='public', csrf=False)
    def ogone_s2s_create_json(self, **kwargs):
        data = kwargs
        acquirer_id = int(data.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        new_id = acquirer.s2s_process(data)
        return new_id

    @http.route(['/payment/ogone/s2s/create'], type='http', auth='public', methods=["POST"], csrf=False)
    def ogone_s2s_create(self, **post):
        acquirer_id = int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        acquirer.s2s_process(post)
        return werkzeug.utils.redirect(post.get('return_url', '/'))

    @http.route(['/payment/ogone/s2s/feedback'], auth='none', csrf=False)
    def feedback(self, **kwargs):
        cr, uid, context = request.cr, SUPERUSER_ID, request.context
        payment = request.registry.get('payment.transaction')
        try:
            tx = payment._ogone_form_get_tx_from_data(cr, uid, kwargs, context=context)
            payment._ogone_s2s_validate(tx)
        except ValidationError:
            return 'ko'

        return 'ok'
