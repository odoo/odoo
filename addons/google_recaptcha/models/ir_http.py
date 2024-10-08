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

    def session_info(self):
        session_info = super().session_info()
        return self._add_public_key_to_session_info(session_info)

    @api.model
    def get_frontend_session_info(self):
        frontend_session_info = super().get_frontend_session_info()
        return self._add_public_key_to_session_info(frontend_session_info)

    @api.model
    def _add_public_key_to_session_info(self, session_info):
        """Add the ReCaptcha public key to the given session_info object"""
        public_key = self.env['ir.config_parameter'].sudo().get_param('recaptcha_public_key')
        if public_key:
            session_info['recaptcha_public_key'] = public_key
        return session_info

    @api.model
    def _verify_request_recaptcha_token(self, action):
        """ Verify the recaptcha token for the current request.
            If no recaptcha private key is set the recaptcha verification
            is considered inactive and this method will return True.
        """
        ip_addr = request.httprequest.remote_addr
        token = request.params.pop('recaptcha_token_response', False)
        recaptcha_result = request.env['ir.http']._verify_recaptcha_token(ip_addr, token, action)
        if recaptcha_result in ['is_human', 'no_secret']:
            return True
        if recaptcha_result == 'wrong_secret':
            raise ValidationError(_("The reCaptcha private key is invalid."))
        elif recaptcha_result == 'wrong_token':
            raise ValidationError(_("The reCaptcha token is invalid."))
        elif recaptcha_result == 'timeout':
            raise UserError(_("Your request has timed out, please retry."))
        elif recaptcha_result == 'bad_request':
            raise UserError(_("The request is invalid or malformed."))
        else:
            return False

    @api.model
    def _verify_recaptcha_token(self, ip_addr, token, action=False):
        """
            Verify a recaptchaV3 token and returns the result as a string.
            RecaptchaV3 verify DOC: https://developers.google.com/recaptcha/docs/verify

            :return: The result of the call to the google API:
                     is_human: The token is valid and the user trustworthy.
                     is_bot: The user is not trustworthy and most likely a bot.
                     no_secret: No reCaptcha secret set in settings.
                     wrong_action: the action performed to obtain the token does not match the one we are verifying.
                     wrong_token: The token provided is invalid or empty.
                     wrong_secret: The private key provided in settings is invalid.
                     timeout: The request has timout or the token provided is too old.
                     bad_request: The request is invalid or malformed.
            :rtype: str
        """
        private_key = request.env['ir.config_parameter'].sudo().get_param('recaptcha_private_key')
        recaptcha_enabled = request.env['ir.config_parameter'].sudo().get_param('recaptcha_enabled')

        if not (private_key and recaptcha_enabled):
            return 'no_secret'
        min_score = request.env['ir.config_parameter'].sudo().get_param('recaptcha_min_score')
        try:
            r = requests.post('https://www.recaptcha.net/recaptcha/api/siteverify', {
                'secret': private_key,
                'response': token,
                'remoteip': ip_addr,
            }, timeout=2)  # it takes ~50ms to retrieve the response
            result = r.json()
            res_success = result['success']
            res_action = res_success and action and result['action']
        except requests.exceptions.Timeout:
            logger.error("Trial captcha verification timeout for ip address %s", ip_addr)
            return 'timeout'
        except Exception:
            logger.error("Trial captcha verification bad request response")
            return 'bad_request'

        if res_success:
            score = result.get('score', False)
            if score < float(min_score):
                logger.warning("Trial captcha verification for ip address %s failed with score %f.", ip_addr, score)
                return 'is_bot'
            if res_action and res_action != action:
                logger.warning("Trial captcha verification for ip address %s failed with action %f, expected: %s.", ip_addr, score, action)
                return 'wrong_action'
            logger.info("Trial captcha verification for ip address %s succeeded with score %f.", ip_addr, score)
            return 'is_human'
        errors = result.get('error-codes', [])
        logger.warning("Trial captcha verification for ip address %s failed error codes %r. token was: [%s]", ip_addr, errors, token)
        for error in errors:
            if error in ['missing-input-secret', 'invalid-input-secret']:
                return 'wrong_secret'
            if error in ['missing-input-response', 'invalid-input-response']:
                return 'wrong_token'
            if error == 'timeout-or-duplicate':
                return 'timeout'
            if error == 'bad-request':
                return 'bad_request'
        return 'is_bot'
