# -*- coding: utf-8 -*-
import logging
import pprint
import werkzeug

from odoo import http, SUPERUSER_ID, _
from odoo.http import request
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment.controllers.portal import PaymentProcessing

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
    ], type='http', auth='public')
    def ogone_form_feedback(self, **post):# used when redirected on ogone website
        """ Ogone contacts using GET, at least for accept """
        _logger.info('Ogone: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'ogone')
        return werkzeug.utils.redirect("/payment/process")

    @http.route(['/payment/ogone/s2s/create_json'], type='json', auth='public', csrf=False)
    def ogone_s2s_create_json(self, **kwargs):
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        new_id = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id'))).s2s_process(kwargs)
        return new_id.id

    @http.route(['/payment/ogone/s2s/create'], type='http', auth='public', methods=["POST"], csrf=False) # verify if used when redirected on ogone website
    def ogone_s2s_create(self, **post):
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
                'accept_url': baseurl + '/payment/ogone/validate/accept',
                'decline_url': baseurl + '/payment/ogone/validate/decline',
                'exception_url': baseurl + '/payment/ogone/validate/exception',
                'return_url': post.get('return_url', baseurl)
                }
            tx = token.validate(**params)
            if tx and tx.html_3ds:
                return tx.html_3ds
            # add the payment transaction into the session to let the page /payment/process to handle it
            PaymentProcessing.add_payment_transaction(tx)
        return werkzeug.utils.redirect("/payment/process")

    @http.route([
        '/payment/ogone/validate/accept',
        '/payment/ogone/validate/decline',
        '/payment/ogone/validate/exception',
    ], type='http', auth='public')
    def ogone_validation_form_feedback(self, **post):
        """ Feedback from 3d secure for a bank card validation """
        request.env['payment.transaction'].sudo().form_feedback(post, 'ogone')
        return werkzeug.utils.redirect("/payment/process")

    @http.route(['/payment/ogone/s2s/feedback'], auth='public', csrf=False)
    def feedback(self, **kwargs):
        try:
            tx = request.env['payment.transaction'].sudo()._ogone_form_get_tx_from_data(kwargs)
            tx._ogone_s2s_validate_tree(kwargs)
        except ValidationError:
            return 'ko'
        return 'ok'

    @http.route(['/payment/ogone/prepare_token', ], type='json', auth='public')
    def prepare_token(self, **kwargs):
        payment_token = request.env['payment.token'].with_user(SUPERUSER_ID)
        data = payment_token.ogone_prepare_token(kwargs)
        return data


    @http.route(['/payment/ogone/feedback', ], type='http', auth='public', website=True, sitemap=False)
    def ogone_alias_gateway_feedback(self, **post):
        post = {key.upper(): value for key, value in post.items()}
        acquirer = request.env['payment.acquirer'].with_user(SUPERUSER_ID).search([('provider', '=', 'ogone')])
        try:
            if not acquirer._ogone_sha_check(post['SHASIGN'], post):
                _logger.error('Ingnico: feeback Alias creation %s', pprint.pformat(post))
                # This may be triggerd if the alias is not created
                error_message = _('We are not able to verify the Signature')
                _logger.error(error_message)
                return request.render("payment_ingenico.payment_error_page", {'error': error_message})
        except KeyError:
            # FIXME better error messages
            _logger.error('Ingenico: feeback Alias creation %s', pprint.pformat(post))
            error_message = _('No payment data provided by the payment acquirer.')
            return request.render("payment_ingenico.payment_error_page", {'error': error_message})

        if 'ACCEPTANCE' in post:
            # Post transaction feedback
            acquirer._ogone_transaction_feedback(post)
            return werkzeug.utils.redirect("/payment/process")
        else:
            # Alias gateway feedback
            feedback = acquirer._ogone_alias_gateway_feedback(post)
            if feedback['success']:
                return request.render("payment_ingenico.payment_feedback_page", feedback['parameters'])
            else:
                return request.render("payment_ingenico.payment_error_page", {'error': feedback['error']})
