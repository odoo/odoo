# -*- coding: utf-8 -*-
import pprint
import logging
from werkzeug import urls, utils

from odoo import http, _
from odoo.http import request
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)


class AuthorizeController(http.Controller):
    _return_url = '/payment/authorize/return/'
    _cancel_url = '/payment/authorize/cancel/'

    @http.route([
        '/payment/authorize/return/',
        '/payment/authorize/cancel/',
    ], type='http', auth='public', csrf=False)
    def authorize_form_feedback(self, **post):
        _logger.info('Authorize: entering form_feedback with post data %s', pprint.pformat(post))
        if post:
            request.env['payment.transaction'].sudo().form_feedback(post, 'authorize')
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        # Authorize.Net is expecting a response to the POST sent by their server.
        # This response is in the form of a URL that Authorize.Net will pass on to the
        # client's browser to redirect them to the desired location need javascript.
        return request.render('payment_authorize.payment_authorize_redirect', {
            'return_url': urls.url_join(base_url, "/payment/process")
        })

    @http.route(['/payment/authorize/s2s/create_json_3ds'], type='json', auth='public', csrf=False)
    def authorize_s2s_create_json_3ds(self, verify_validity=False, **kwargs):
        token = False
        acquirer = request.env['payment.acquirer'].browse(int(kwargs.get('acquirer_id')))

        try:
            if not kwargs.get('partner_id'):
                kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
            token = acquirer.s2s_process(kwargs)
        except ValidationError as e:
            message = e.args[0]
            if isinstance(message, dict) and 'missing_fields' in message:
                if request.env.user._is_public():
                    message = _("Please sign in to complete the payment.")
                    # update message if portal mode = b2b
                    if request.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'false':
                        message += _(" If you don't have any account, ask your salesperson to grant you a portal access. ")
                else:
                    msg = _("The transaction cannot be processed because some contact details are missing or invalid: ")
                    message = msg + ', '.join(message['missing_fields']) + '. '
                    message += _("Please complete your profile. ")

            return {
                'error': message
            }

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
            'verified': True, #Authorize.net does a transaction type of Authorization Only
                              #As Authorize.net already verify this card, we do not verify this card again.
        }
        #token.validate() don't work with Authorize.net.
        #Payments made via Authorize.net are settled and allowed to be refunded only on the next day.
        #https://account.authorize.net/help/Miscellaneous/FAQ/Frequently_Asked_Questions.htm#Refund
        #<quote>The original transaction that you wish to refund must have a status of Settled Successfully.
        #You cannot issue refunds against unsettled, voided, declined or errored transactions.</quote>
        return res

    @http.route(['/payment/authorize/s2s/create'], type='http', auth='public')
    def authorize_s2s_create(self, **post):
        acquirer_id = int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        acquirer.s2s_process(post)
        return utils.redirect("/payment/process")
