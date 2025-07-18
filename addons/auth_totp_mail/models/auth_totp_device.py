# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models


class Auth_TotpDevice(models.Model):
    _inherit = "auth_totp.device"

    def unlink(self):
        """ Notify users when trusted devices are removed from their account. """
        removed_devices_by_user = self.grouped('user_id')
        for user, removed_devices in removed_devices_by_user.items():
            user._notify_security_setting_update(
                _("Security Update: Device Removed"),
                _(
                    "A trusted device has just been removed from your account: %(device_names)s",
                    device_names=', '.join([device.name for device in removed_devices])
                ),
            )

        return super().unlink()
