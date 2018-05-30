# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug
from werkzeug.urls import url_unquote_plus

from odoo import http
from odoo.http import request
from odoo.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)


class IngenicoController(http.Controller):
    _accept_url = '/payment/ingenico/test/accept'
    _decline_url = '/payment/ingenico/test/decline'
    _exception_url = '/payment/ingenico/test/exception'
    _cancel_url = '/payment/ingenico/test/cancel'

    @http.route([
        '/payment/ingenico/accept', '/payment/ingenico/test/accept',
        '/payment/ingenico/decline', '/payment/ingenico/test/decline',
        '/payment/ingenico/exception', '/payment/ingenico/test/exception',
        '/payment/ingenico/cancel', '/payment/ingenico/test/cancel',
    ], type='http', auth='none')
    def ingenico_form_feedback(self, **post):
        """ Ingenico contacts using GET, at least for accept """
        _logger.info('Ingenico: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'ingenico')
        return werkzeug.utils.redirect(url_unquote_plus(post.pop('return_url', '/')))

    @http.route(['/payment/ingenico/s2s/create_json'], type='json', auth='public', csrf=False)
    def ingenico_s2s_create_json(self, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        new_id = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        return new_id.id

    @http.route(['/payment/ingenico/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def ingenico_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        token = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)

        if not token:
            res = {
                'result': False,
            }
            return res

        res = {
            'result': True,
            'id': token.id,
            'short_name': token.short_name,
            '3d_secure': False,
            'verified': False,
        }

        if verify_validity != False:
            baseurl = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            params = {
                'accept_url': baseurl + '/payment/ingenico/validate/accept',
                'decline_url': baseurl + '/payment/ingenico/validate/decline',
                'exception_url': baseurl + '/payment/ingenico/validate/exception',
                'return_url': kwargs.get('return_url', baseurl)
                }
            tx = token.validate(**params)
            res['verified'] = token.verified

            if tx and tx.html_3ds:
                res['3d_secure'] = tx.html_3ds

        return res

    @http.route(['/payment/ingenico/s2s/create'], type='http', auth='public', methods=["POST"], csrf=False)
    def ingenico_s2s_create(self, **post):
        error = ''
        acq = request.env['payment.acquirer'].browse(int(post.get('acquirer_id')))
        try:
            token = acq.s2s_process(post)
        except Exception as e:
            # synthax error: 'CHECK ERROR: |Not a valid date\n\n50001111: None'
            token = False
            error = str(e).splitlines()[0].split('|')[-1] or ''

        if token and post.get('verify_validity'):
            baseurl = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
            params = {
                'accept_url': baseurl + '/payment/ingenico/validate/accept',
                'decline_url': baseurl + '/payment/ingenico/validate/decline',
                'exception_url': baseurl + '/payment/ingenico/validate/exception',
                'return_url': post.get('return_url', baseurl)
                }
            tx = token.validate(**params)
            if tx and tx.html_3ds:
                return tx.html_3ds
        return werkzeug.utils.redirect(post.get('return_url', '/') + (error and '#error=%s' % werkzeug.url_quote(error) or ''))

    @http.route([
        '/payment/ingenico/validate/accept',
        '/payment/ingenico/validate/decline',
        '/payment/ingenico/validate/exception',
    ], type='http', auth='none')
    def ingenico_validation_form_feedback(self, **post):
        """ Feedback from 3d secure for a bank card validation """
        request.env['payment.transaction'].sudo().form_feedback(post, 'ingenico')
        return werkzeug.utils.redirect(werkzeug.url_unquote(post.pop('return_url', '/')))

    @http.route(['/payment/ingenico/s2s/feedback'], auth='none', csrf=False)
    def feedback(self, **kwargs):
        try:
            tx = request.env['payment.transaction'].sudo()._ingenico_form_get_tx_from_data(kwargs)
            tx._ingenico_s2s_validate_tree(kwargs)
        except ValidationError:
            return 'ko'
        return 'ok'
