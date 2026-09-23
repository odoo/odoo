import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.tools.misc import str2bool

logger = logging.getLogger(__name__)

#: How much of a failed captcha token reaches the log. The value is
#: attacker-controlled, so it is truncated rather than written whole.
TOKEN_LOG_PREFIX = 12


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    def session_info(self):
        session_info = super().session_info()
        return self._add_public_key_to_session_info(session_info)

    @api.model
    def get_frontend_session_info(self):
        frontend_session_info = super().get_frontend_session_info()
        return self._add_public_key_to_session_info(frontend_session_info)

    @api.model
    def _is_recaptcha_enabled(self):
        """Return whether reCAPTCHA verification is enabled."""
        config_params = self.env["ir.config_parameter"].sudo()
        return str2bool(config_params.get_param("enable_recaptcha", default=True))

    @api.model
    def _add_public_key_to_session_info(self, session_info):
        """Add the ReCaptcha public key to the given session_info object"""
        config_params = self.env["ir.config_parameter"].sudo()
        public_key = config_params.get_param("recaptcha_public_key")
        if public_key and self._is_recaptcha_enabled():
            session_info["recaptcha_public_key"] = public_key
        return session_info

    @api.model
    def _check_request_recaptcha_token(self, action):
        """Verify the recaptcha token for the current request.
        If no recaptcha private key is set the recaptcha verification
        is considered inactive and this method returns without raising.
        """
        super()._check_request_recaptcha_token(action)
        if not self._is_recaptcha_enabled():
            return
        ip_addr = request.httprequest.remote_addr
        token = request.params.pop("recaptcha_token_response", False)
        recaptcha_result = request.env["ir.http"]._get_recaptcha_verdict(
            ip_addr, token, action
        )
        if recaptcha_result in ["is_human", "no_secret"]:
            return
        if recaptcha_result == "wrong_secret":
            raise ValidationError(_("The reCaptcha private key is invalid."))
        if recaptcha_result == "wrong_token":
            raise ValidationError(_("The reCaptcha token is invalid."))
        if recaptcha_result == "timeout":
            raise UserError(_("Your request has timed out, please retry."))
        if recaptcha_result == "bad_request":
            raise UserError(_("The request is invalid or malformed."))
        raise UserError(_("Suspicious activity detected by google reCAPTCHA."))

    @api.model
    def _get_recaptcha_verdict(self, ip_addr, token, action=False):
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
        private_key = request.env["credential.credential"]._get_system_secret(
            "recaptcha_private_key"
        )
        if not private_key:
            return "no_secret"
        min_score = (
            request.env["ir.config_parameter"]
            .sudo()
            .get_param_float("recaptcha_min_score", 0.7)
        )
        try:
            r = self.env["ir.egress"].request(
                "POST",
                "https://www.recaptcha.net/recaptcha/api/siteverify",
                purpose="recaptcha",
                data={
                    "secret": private_key,
                    "response": token,
                    "remoteip": ip_addr,
                },
                timeout=2,
            )  # it takes ~50ms to retrieve the response
            result = r.json()
            res_success = result["success"]
            res_action = res_success and action and result["action"]
        except requests.exceptions.Timeout:
            logger.error(
                "Trial captcha verification timeout for ip address %s", ip_addr
            )
            return "timeout"
        except Exception as e:
            # The class, not the message: the message is the one thing here
            # that could in principle echo back something we sent. It cannot
            # carry the secret -- that travels in the POST body, never a URL --
            # but the class alone already separates a TLS error from a JSON
            # parse error from the KeyError this same clause catches when
            # Google's response changes shape.
            logger.error(
                "Trial captcha verification bad request response (%s)",
                type(e).__name__,
            )
            return "bad_request"

        if res_success:
            if "score" not in result:
                # v3 always scores a successful verification, so a success with
                # no score means the response is not the one this code reads --
                # a v2 site key, an API change, something in the middle. It used
                # to fall through as `False`, which compares as 0: harmless at
                # the default threshold, accepted as human at a threshold of 0,
                # and in both cases logged as a score of 0.000000 that Google
                # never sent.
                logger.warning(
                    "Trial captcha verification for ip address %s returned no score; "
                    "treating as a failure.",
                    ip_addr,
                )
                return "bad_request"
            score = result["score"]
            if score < min_score:
                logger.warning(
                    "Trial captcha verification for ip address %s failed with score %f.",
                    ip_addr,
                    score,
                )
                return "is_bot"
            if res_action and res_action != action:
                logger.warning(
                    "Trial captcha verification for ip address %s failed with action %s, expected: %s.",
                    ip_addr,
                    res_action,
                    action,
                )
                return "wrong_action"
            logger.info(
                "Trial captcha verification for ip address %s succeeded with score %f.",
                ip_addr,
                score,
            )
            return "is_human"
        errors = result.get("error-codes", [])
        # The token is an attacker-controlled request parameter bounded only by
        # DEFAULT_MAX_CONTENT_LENGTH (128 MB), and this line runs once per failed
        # verification on public routes: logging it whole let a caller choose how
        # much we write to disk. A short prefix is enough to correlate a report
        # with a request; the error codes are the actual diagnostic.
        logger.warning(
            "Trial captcha verification for ip address %s failed error codes %r. token prefix was: [%s]",
            ip_addr,
            errors,
            (token or "")[:TOKEN_LOG_PREFIX],
        )
        for error in errors:
            if error in ["missing-input-secret", "invalid-input-secret"]:
                return "wrong_secret"
            if error in ["missing-input-response", "invalid-input-response"]:
                return "wrong_token"
            if error == "timeout-or-duplicate":
                return "timeout"
            if error == "bad-request":
                return "bad_request"
        return "is_bot"
