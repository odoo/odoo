# -*- coding: utf-8 -*-
from odoo import models
from odoo.addons.auth_totp.controllers.home import TRUSTED_DEVICE_AGE_DAYS

import logging
_logger = logging.getLogger(__name__)


class Auth_TotpDevice(models.Model):

    # init is overriden in res.users.apikeys to create a secret column 'key'
    # use a different model to benefit from the secured methods while not mixing
    # two different concepts

    _name = 'auth_totp.device'
    _inherit = ["res.users.apikeys"]
    _description = "Authentication Device"
    _auto = False

    def _check_credentials_for_uid(self, *, scope, key, uid):
        """Return True if device key matches given `scope` for user ID `uid`"""
        assert uid, "uid is required"
        return self._check_credentials(scope=scope, key=key) == uid

    def _get_trusted_device_age(self):
        ICP = self.env['ir.config_parameter'].sudo()
        try:
            nbr_days = int(ICP.get_param('auth_totp.trusted_device_age', TRUSTED_DEVICE_AGE_DAYS))
            if nbr_days <= 0:
                nbr_days = None
        except ValueError:
            nbr_days = None

        if nbr_days is None:
            _logger.warning("Invalid value for 'auth_totp.trusted_device_age', using default value.")
            nbr_days = TRUSTED_DEVICE_AGE_DAYS

        return nbr_days * 86400  # seconds
