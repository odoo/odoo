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

    @http.route(['/payment/authorize/s2s/create_json'], type='json', auth='public')
    def authorize_s2s_create_json(self, **kwargs):
        acquirer_id = int(kwargs.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        if not kwargs.get('partner_id'):
            kwargs = dict(kwargs, partner_id=request.env.user.partner_id.id)
        try:
           return acquirer.s2s_process(kwargs).id
        except (ValidationError, UserError) as e:
           return {
               'error': e.name,
           }

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
                msg = _("The transaction cannot be processed because some contact details are missing or invalid: ")
                message = msg + ', '.join(message['missing_fields']) + '. '
                if request.env.user._is_public():
                    message += _("Please sign in to complete your profile.")
                    # update message if portal mode = b2b
                    if request.env['ir.config_parameter'].sudo().get_param('auth_signup.allow_uninvited', 'False').lower() == 'false':
                        message += _("If you don't have any account, please ask your salesperson to update your profile. ")
                else:
                    message += _("Please complete your profile. ")

            return {
                'error': message
            }
        except UserError as e:
            return {
                'error': e.name,
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
            'verified': False,
        }

        if verify_validity != False:
            token.validate()
            res['verified'] = token.verified

        return res

    @http.route(['/payment/authorize/s2s/create'], type='http', auth='public')
    def authorize_s2s_create(self, **post):
        acquirer_id = int(post.get('acquirer_id'))
        acquirer = request.env['payment.acquirer'].browse(acquirer_id)
        acquirer.s2s_process(post)
        return utils.redirect("/payment/process")
