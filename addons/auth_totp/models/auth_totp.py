# -*- coding: utf-8 -*-
from odoo import models

import logging
from odoo.addons import base
_logger = logging.getLogger(__name__)


class Auth_TotpDevice(models.Model, base.ResUsersApikeys):

    # init is overriden in res.users.apikeys to create a secret column 'key'
    # use a different model to benefit from the secured methods while not mixing
    # two different concepts

    _description = "Authentication Device"
    _auto = False

    def _check_credentials_for_uid(self, *, scope, key, uid):
        """Return True if device key matches given `scope` for user ID `uid`"""
        assert uid, "uid is required"
        return self._check_credentials(scope=scope, key=key) == uid
