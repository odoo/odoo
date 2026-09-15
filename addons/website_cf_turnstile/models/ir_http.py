import logging

import requests

from odoo import _, api, models
from odoo.exceptions import UserError, ValidationError
from odoo.http import request
from odoo.libs.debug_log import DebugLog

logger = logging.getLogger(__name__)
_debug = DebugLog(__name__)


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @api.model
    def get_frontend_session_info(self):
        session = super().get_frontend_session_info()

        site_key = (
            self.env["ir.config_parameter"].sudo().get_param("cf.turnstile_site_key")
        )
        if site_key:
            session["turnstile_site_key"] = site_key

        return session

    @api.model
    def _check_request_recaptcha_token(self, action):
        super()._check_request_recaptcha_token(action)
        ip_addr = request.httprequest.remote_addr
        token = request.params.pop("turnstile_captcha", False)
        turnstile_result = request.env["ir.http"]._get_turnstile_verdict(
            ip_addr, token, action
        )
        if turnstile_result in ["is_human", "no_secret"]:
            return
        _debug.logic("turnstile_refused", verdict=turnstile_result)
        if turnstile_result == "wrong_secret":
            raise ValidationError(_("The Cloudflare turnstile private key is invalid."))
        if turnstile_result == "wrong_token":
            raise ValidationError(_("The CloudFlare human validation failed."))
        if turnstile_result == "timeout":
            raise UserError(_("Your request has timed out, please retry."))
        if turnstile_result == "bad_request":
            raise UserError(_("The request is invalid or malformed."))
        raise UserError(_("Suspicious activity detected by Turnstile CAPTCHA."))

    @api.model
    def _get_turnstile_verdict(self, ip_addr, token, action=False):
        private_key = request.env["credential.credential"]._get_system_secret(
            "cf.turnstile_secret_key"
        )
        if not private_key:
            return "no_secret"
        try:
            r = self.env["ir.egress"].request(
                "POST",
                "https://challenges.cloudflare.com/turnstile/v0/siteverify",
                purpose="turnstile",
                data={
                    "secret": private_key,
                    "response": token,
                    "remoteip": ip_addr,
                },
                timeout=3.05,
            )
            result = r.json()
            res_success = result["success"]
            res_action = res_success and action and result["action"]
        except requests.exceptions.Timeout:
            logger.error("Turnstile verification timeout for ip address %s", ip_addr)
            return "timeout"
        except Exception:
            logger.error("Turnstile verification bad request response")
            return "bad_request"

        if res_success:
            if res_action and res_action != action:
                logger.warning(
                    "Turnstile verification for ip address %s failed with action %f, expected: %s.",
                    ip_addr,
                    res_action,
                    action,
                )
                return "wrong_action"
            logger.info("Turnstile verification for ip address %s succeeded", ip_addr)
            return "is_human"
        errors = result.get("error-codes", [])
        logger.warning(
            "Turnstile verification for ip address %s failed error codes %r. token was: [%s]",
            ip_addr,
            errors,
            token,
        )
        for error in errors:
            if error in ["missing-input-secret", "invalid-input-secret"]:
                return "wrong_secret"
            if error in ["missing-input-response", "invalid-input-response"]:
                return "wrong_token"
            if error in ("timeout-or-duplicate", "internal-error"):
                return "timeout"
            if error == "bad-request":
                return "bad_request"
        return "is_bot"
