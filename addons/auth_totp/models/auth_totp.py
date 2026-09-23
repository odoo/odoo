import logging

from odoo import models
from odoo.exceptions import AccessError

from odoo.addons.auth_totp.controllers.home import TRUSTED_DEVICE_AGE_DAYS

_logger = logging.getLogger(__name__)


class Auth_TotpDevice(models.Model):
    # init is overriden in res.users.apikeys to create a secret column 'key'
    # use a different model to benefit from the secured methods while not mixing
    # two different concepts

    _name = "auth_totp.device"
    _inherit = ["res.users.apikeys"]
    _description = "Authentication Device"
    _auto = False

    def _check_generate_access(self):
        """A trusted device is not an API key, and is not gated like one.

        The prototype above is borrowed for the hashed-secret column and the
        constant-time lookup, deliberately "while not mixing two different
        concepts" -- but ``res.users.apikeys._check_generate_access`` is a
        policy about the other concept: who may mint *credentials that replace
        a password over RPC*. Inheriting it meant portal's widening of that
        policy also governed 2FA, so a portal user ticking "remember this
        device" got an AccessError -- an HTTP 403 on the login POST, with the
        session already finalized -- unless an administrator had switched on
        ``portal.allow_api_keys``, a setting labelled "Customers can generate
        API Keys" and about something else entirely.

        Remembering a browser is the user's own decision about their own
        account, and the only caller (``/web/login/totp``) reaches this line
        having already verified a full first factor and a valid TOTP code. The
        public user is still refused: it authenticates nothing and any device
        minted for it would be shared by every anonymous visitor.

        :raises AccessError: if there is no authenticated user to trust.
        """
        if self.env.user._is_public():
            raise AccessError(
                self.env._("Only an authenticated user can register a trusted device")
            )

    def _check_credentials_for_uid(self, *, scope, key, uid):
        """Return True if device key matches given `scope` for user ID `uid`"""
        assert uid, "uid is required"
        return self._check_credentials(scope=scope, key=key) == uid

    def _get_trusted_device_age(self):
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            nbr_days = int(
                ICP.get_param("auth_totp.trusted_device_age", TRUSTED_DEVICE_AGE_DAYS)
            )
            if nbr_days <= 0:
                nbr_days = None
        except ValueError:
            nbr_days = None

        if nbr_days is None:
            _logger.warning(
                "Invalid value for 'auth_totp.trusted_device_age', using default value."
            )
            nbr_days = TRUSTED_DEVICE_AGE_DAYS

        return nbr_days * 86400  # seconds
