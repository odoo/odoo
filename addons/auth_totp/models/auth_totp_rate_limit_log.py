# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models

TOTP_RATE_LIMITS = {
    'totp_code_check': (5, 3600),
    'totp_send_email': (5, 3600),
}

TOTP_RATE_LIMIT_MESSAGES = {
    'totp_send_email': _(
        'You reached the limit of authentication mails sent for your account,'
        ' please try again later.'
    ),
    'totp_code_check': _(
        'You reached the limit of code verifications for your account,'
        ' please try again later.'
    ),
}


class RateLimitLog(models.TransientModel):
    _inherit = 'rate.limit.log'

    def _rate_limit_get_config(self, scope):
        if scope in TOTP_RATE_LIMITS:
            return TOTP_RATE_LIMITS[scope]
        return super()._rate_limit_get_config(scope)

    def _rate_limit_get_error_message(self, scope):
        if scope in TOTP_RATE_LIMIT_MESSAGES:
            return TOTP_RATE_LIMIT_MESSAGES[scope]
        return super()._rate_limit_get_error_message(scope)
