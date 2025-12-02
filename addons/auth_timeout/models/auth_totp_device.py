from odoo import models


class AuthTotpDevice(models.Model):
    _inherit = "auth_totp.device"

    def _get_trusted_device_age(self):
        age = super()._get_trusted_device_age()
        user_lock_timeout_mfa = [
            threshold for threshold, mfa in self.env.user._get_lock_timeouts().get("lock_timeout") if mfa
        ]
        if user_lock_timeout_mfa:
            return min(age, *user_lock_timeout_mfa)
        return age
