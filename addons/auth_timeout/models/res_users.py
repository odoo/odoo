from odoo import models


class ResUsers(models.Model):
    _inherit = "res.users"

    def _get_auth_methods(self):
        """
        Return the list of authentication methods available to the user.

        This includes passkeys (WebAuthn), TOTP (app or mail), and password,
        depending on the user's configured credentials and MFA policy.

        :return: A list of enabled authentication method types (e.g., ["webauthn", "totp", "password"]).
        :rtype: list[str]
        """
        self.ensure_one()
        auth_methods = []
        if self.auth_passkey_key_ids:
            auth_methods.append("webauthn")
        if mfa_type := self._mfa_type():
            auth_methods.append(mfa_type)
        auth_methods.append("password")
        return auth_methods

    def _get_lock_timeouts(self):
        """
        Return the user's configured session and inactivity timeouts.

        Delegates to the group-level `_get_lock_timeouts`, using the user's group membership
        to determine applicable timeout settings.

        :return: A dictionary of timeout types and values, as defined by `_get_lock_timeouts` on groups.
        :rtype: dict
        """
        self.ensure_one()
        # Take advantage of the ormcache of `self._get_group_ids()` to get the user groups and avoid queries
        return self.env["res.groups"].browse(self._get_group_ids())._get_lock_timeouts()

    def _get_lock_timeout_inactivity(self):
        """
        Return the shortest applicable inactivity timeout for the user.

        Extracts the first (i.e., shortest) timeout from the "lock_timeout_inactivity"
        entry in the user's timeout configuration, if present.

        :return: Inactivity timeout in seconds, or None if not configured.
        :rtype: float or None
        """
        timeouts = self._get_lock_timeouts()
        return timeouts.get("lock_timeout_inactivity")[0][0] if timeouts.get("lock_timeout_inactivity") else None
