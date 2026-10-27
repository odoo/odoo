# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.
import logging
import requests

from odoo import api, models, _
from odoo.http import request
from odoo.exceptions import UserError, ValidationError

logger = logging.getLogger(__name__)


class Http(models.AbstractModel):
    _inherit = 'ir.http'

    @api.model
    def get_frontend_session_info(self):
        """Add the Turnstile public key to the given session_info object"""
        session = super().get_frontend_session_info()

        site_key = self.env['ir.config_parameter'].sudo().get_param('cf.turnstile_site_key')
        if site_key:
            session['turnstile_site_key'] = site_key

        return session

    @api.model
    def _verify_request_recaptcha_token(self, action):
        """ Verify the recaptcha token for the current request.
            If no recaptcha private key is set the recaptcha verification
            is considered inactive and this method will return True.
        """
        res = super()._verify_request_recaptcha_token(action)

        if not res:  # check result of google_recaptcha
            return res

        ip_addr = request.httprequest.remote_addr
        token = request.params.pop('turnstile_captcha', False)
        turnstile_result = request.env['ir.http']._verify_turnstile_token(ip_addr, token, action)
        if turnstile_result in ['is_human', 'no_secret']:
            return True
        if turnstile_result == 'wrong_secret':
            raise ValidationError(_("The Cloudflare turnstile private key is invalid."))
        elif turnstile_result == 'wrong_token':
            raise ValidationError(_("The CloudFlare human validation failed."))
        elif turnstile_result == 'timeout':
            raise UserError(_("Your request has timed out, please retry."))
        elif turnstile_result == 'bad_request':
            raise UserError(_("The request is invalid or malformed."))
        else:  # wrong_action e.g.
            return False

    @api.model
    def _verify_turnstile_token(self, ip_addr, token, action=False):
        """
            Verify a turnstile token and returns the result as a string.
            Turnstile verify DOC: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/

            :return: The result of the call to the cloudflare API:
                     is_human: The token is valid and the user trustworthy.
                     is_bot: The user is not trustworthy and most likely a bot.
                     no_secret: No private key in settings.
                     wrong_action: the action performed to obtain the token does not match the one we are verifying.
                     wrong_token: The token provided is invalid or empty.
                     wrong_secret: The private key provided in settings is invalid.
                     timeout: The request has timout or the token provided is too old.
                     bad_request: The request is invalid or malformed.
                     internal-error: The request failed.
            :rtype: str
        """
        private_key = request.env['ir.config_parameter'].sudo().get_param('cf.turnstile_secret_key')
        if not private_key:
            return 'no_secret'
        try:
            r = requests.post('https://challenges.cloudflare.com/turnstile/v0/siteverify', {
                'secret': private_key,
                'response': token,
                'remoteip': ip_addr,
            }, timeout=3.05)
            result = r.json()
            res_success = result['success']
            res_action = res_success and action and result['action']
        except requests.exceptions.Timeout:
            logger.error("Turnstile verification timeout for ip address %s", ip_addr)
            return 'timeout'
        except Exception:
            logger.error("Turnstile verification bad request response")
            return 'bad_request'

        if res_success:
            if res_action and res_action != action:
                logger.warning("Turnstile verification for ip address %s failed with action %f, expected: %s.", ip_addr, res_action, action)
                return 'wrong_action'
            logger.info("Turnstile verification for ip address %s succeeded", ip_addr)
            return 'is_human'
        errors = result.get('error-codes', [])
        logger.warning("Turnstile verification for ip address %s failed error codes %r. token was: [%s]", ip_addr, errors, token)
        for error in errors:
            if error in ['missing-input-secret', 'invalid-input-secret']:
                return 'wrong_secret'
            if error in ['missing-input-response', 'invalid-input-response']:
                return 'wrong_token'
            if error in ('timeout-or-duplicate', 'internal-error'):
                return 'timeout'
            if error == 'bad-request':
                return 'bad_request'
        return 'is_bot'
