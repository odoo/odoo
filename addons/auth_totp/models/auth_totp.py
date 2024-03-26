# -*- coding: utf-8 -*-

import logging
from collections import defaultdict

from odoo import _, api, models

from odoo.addons.auth_totp.controllers.home import TRUSTED_DEVICE_AGE

_logger = logging.getLogger(__name__)


class AuthTotpDevice(models.Model):

    # init is overriden in res.users.apikeys to create a secret column 'key'
    # use a different model to benefit from the secured methods while not mixing
    # two different concepts

    _name = "auth_totp.device"
    _inherit = "res.users.apikeys"
    _description = "Authentication Device"
    _auto = False

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

    def _check_credentials_for_uid(self, *, scope, key, uid):
        """Return True if device key matches given `scope` for user ID `uid`"""
        assert uid, "uid is required"
        return self._check_credentials(scope=scope, key=key) == uid

    @api.autovacuum
    def _gc_device(self):
        self._cr.execute("""
            DELETE FROM auth_totp_device
            WHERE create_date < (NOW() AT TIME ZONE 'UTC' - INTERVAL '%s SECONDS')
        """, [TRUSTED_DEVICE_AGE])
        _logger.info("GC'd %d totp devices entries", self._cr.rowcount)

    def _generate(self, scope, name):
        """ Notify users when trusted devices are added onto their account.
        We override this method instead of 'create' as those records are inserted directly into the
        database using raw SQL. """

        res = super()._generate(scope, name)

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
