from datetime import timedelta

from odoo import http
from .rate_limiter import RateLimiter

_username_rate_limiter = RateLimiter(1, timedelta(hours=1))
_ip_rate_limiter = RateLimiter(10, timedelta(hours=1))


class PasswordLeakCheckController(http.Controller):
    @http.route('/login/get_password_leak_check_settings', type='json', auth='none')
    def get_password_leak_check_settings(self):
        config = http.request.env['ir.config_parameter'].sudo()
        enabled = config.get_param("auth_password_policy.leak_check_enabled")
        frequency_count = config.get_param("auth_password_policy.leak_check_frequency_count")
        frequency_unit = config.get_param("auth_password_policy.leak_check_frequency_unit")

        return {
            "enabled": enabled == "True",  # str -> bool
            "frequency_count": frequency_count,
            "frequency_unit": frequency_unit,
        }

    @http.route('/login/password_leak_check_performed', type='json', auth='none')
    def password_leak_check_performed(self, username: str, is_password_leaked: bool):
        user = http.request.env['res.users'].sudo().search([('login', '=', username)])
        if not user:
            return {"error": "User not found"}

        rate_limited = _username_rate_limiter.is_rate_limited(username)
        rate_limited |= _ip_rate_limiter.is_rate_limited(http.request.httprequest.remote_addr)
        if rate_limited:
            return {"error": "Rate limit exceeded"}

        user._password_leak_check_performed(is_password_leaked)
