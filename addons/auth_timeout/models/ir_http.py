import time

from odoo import api, models
from odoo.http import request
from odoo.http.session import session_store


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _must_check_identity(cls):
        """
        This method checks two timeout conditions:
        - `lock_timeout`: maximum allowed session duration before re-authentication is required,
        regardless of user activity.
        - `lock_timeout_inactivity`: period of inactivity after which re-authentication is required.

        It compares the current time to session timestamps and evaluates whether the thresholds have been exceeded:
        - `lock_timeout` compares with the session timestamp `create_time`
        - `lock_timeout_inactivity` compares with the session timestamp `identity-check-next`
        """
        reauth_requirements = super()._must_check_identity()
        if reauth_requirements:
            return reauth_requirements

        session = request.session
        env = request.env(user=request.session.uid)
        timeouts = env.user._get_lock_timeouts()
        for timeout_type, reauth_type, session_key, session_key_default, first_timeout in [
            ("lock_timeout", "logout", "create_time", 0, 0),
            (
                "lock_timeout_inactivity",
                "check_identity",
                "identity-check-next",
                None,
                timeouts["lock_timeout_inactivity"][0][0] if timeouts.get("lock_timeout_inactivity") else 0,
            ),
        ]:
            for timeout, mfa in reversed(timeouts[timeout_type]):
                threshold = time.time() - timeout
                timestamp = session.get(session_key, session_key_default)
                # Only the lowest inactivity timeout will set `identity-check-next` in the session
                # Hence, an inactivity timeout with a greater timeout must reduce its timeout with the first timeout
                # to get if its timeout is reached according to when `identity-check-next` was set at the lowest timeout
                # It doesn't apply for `create_time`, which is set as soon as the session is created
                if timestamp is not None and timestamp - first_timeout <= threshold:
                    reauth_requirements = {reauth_type: True, "mfa": mfa}
                    if mfa:
                        first_fa = session.get("identity-check-1fa")
                        if first_fa:
                            timestamp_1fa, auth_method_1fa = first_fa
                            if timestamp_1fa > threshold:
                                reauth_requirements["1fa_method"] = auth_method_1fa
                    break
        return reauth_requirements

    @classmethod
    def _check_identity(cls, credential):
        res = super()._check_identity(credential)
        if res is None:  # User has validated the requirements
            request.session.pop('identity-check-next', None)
        return res

    def _set_session_inactivity(self, session, inactivity_period=0, force=False):
        """
        Set or clear the session's inactivity timeout flag.

        This method is used to track user inactivity and determine when a session
        should trigger re-authentication. It is called when presence data is received
        through the websocket, either:

        - because the web client, in Javascript, sent an event that the user is inactive
        - because the websocket connection was closed (e.g., the user closed the browser,
          the last tab to Odoo was closed, internet disconnection, ...)

        :param Session session: The user's HTTP session object.
        :param float inactivity_period: Duration of user inactivity in milliseconds.
        :param bool force: If True, forcibly mark the session as inactive regardless of duration.
            This is typically used when the WebSocket connection is closed (e.g., the user closes
            their last browser tab), signaling that the user has gone away. The inactivity timeout
            still applies in this case. If the user becomes active again (e.g., reopens the tab)
            before the threshold is reached, the session will be considered active again,
            and re-authentication will not be required.

        :return: None
        """
        # inactivity_period sent by the js is in milliseconds
        inactivity_period = inactivity_period / 1000
        timeout = self.env.user._get_lock_timeout_inactivity()
        inactive = timeout and (force or inactivity_period >= timeout)
        if inactive:
            next_check = time.time() + timeout - inactivity_period
            if not session.get("identity-check-next") or next_check < session["identity-check-next"]:
                session["identity-check-next"] = next_check
                # Save manually, websocket requests do not save the session automatically
                session_store().save(session)
        elif not inactive and (timestamp := session.get("identity-check-next")) and timestamp > time.time():
            session.pop("identity-check-next")
            # Save manually, websocket requests do not save the session automatically
            session_store().save(session)

    def _session_info_common_auth_timeout(self, session_info):
        """
        Add inactivity timeout metadata to the session info dictionary.

        This method is used to include the user's applicable inactivity timeout
        (in seconds) in the session information returned to the frontend. The
        timeout is only added for authenticated (non-public) users.

        :param dict session_info: The original session information dictionary.
        :return: The updated session information with inactivity timeout (if applicable).
        :rtype: dict
        """
        if not self.env.user._is_public() and (timeout := self.env.user._get_lock_timeout_inactivity()):
            session_info["lock_timeout_inactivity"] = timeout
        return session_info

    def session_info(self):
        """
        Extend the backend session info with inactivity timeout metadata.

        Adds the user's inactivity timeout (if applicable) to the session info
        returned to the backend web client.

        :return: The updated session information dictionary.
        :rtype: dict
        """
        session_info = super().session_info()
        return self._session_info_common_auth_timeout(session_info)

    @api.model
    def get_frontend_session_info(self):
        """
        Extend the frontend session info with inactivity timeout and user login.

        dds the user's inactivity timeout (if applicable) to the session info
        returned to the frontend web client.

        :return: The updated session information dictionary.
        :rtype: dict
        """
        session_info = super().get_frontend_session_info()
        return self._session_info_common_auth_timeout(session_info)
