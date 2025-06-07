# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import _, models
from collections import defaultdict


class AuthTotpDevice(models.Model):
    _inherit = "auth_totp.device"

    def unlink(self):
        """ Notify users when trusted devices are removed from their account. """
        removed_devices_by_user = self._classify_by_user()
        for user, removed_devices in removed_devices_by_user.items():
            user._notify_security_setting_update(
                _("Security Update: Device Removed"),
                _(
                    "A trusted device has just been removed from your account: %(device_names)s",
                    device_names=', '.join([device.name for device in removed_devices])
                ),
            )

        return super().unlink()

    def _generate(self, scope, name, expiration_date):
        """ Notify users when trusted devices are added onto their account.
        We override this method instead of 'create' as those records are inserted directly into the
        database using raw SQL. """

        res = super()._generate(scope, name, expiration_date)

        self.env.user._notify_security_setting_update(
            _("Security Update: Device Added"),
            _(
                "A trusted device has just been added to your account: %(device_name)s",
                device_name=name
            ),
        )

        return res

    def _classify_by_user(self):
        devices_by_user = defaultdict(lambda: self.env['auth_totp.device'])
        for device in self:
            devices_by_user[device.user_id] |= device

        return devices_by_user
