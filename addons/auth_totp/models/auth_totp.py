# -*- coding: utf-8 -*-
from odoo import api, models
from odoo.addons.auth_totp.controllers.home import TRUSTED_DEVICE_AGE

import logging
_logger = logging.getLogger(__name__)


class AuthTotpDevice(models.Model):

    # init is overriden in res.users.apikeys to create a secret column 'key'
    # use a different model to benefit from the secured methods while not mixing
    # two different concepts

    _name = "auth_totp.device"
    _inherit = "res.users.apikeys"
    _description = "Authentication Device"
    _auto = False

    @api.autovacuum
    def _gc_device(self):
        self._cr.execute("""
            DELETE FROM auth_totp_device
            WHERE create_date < (NOW() AT TIME ZONE 'UTC' - INTERVAL '%s SECONDS')
        """, [TRUSTED_DEVICE_AGE])
        _logger.info("GC'd %d totp devices entries", self._cr.rowcount)
