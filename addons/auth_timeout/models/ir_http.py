import logging
import re
import time

from odoo import api, models
from odoo.http import request, root, SessionExpiredException


class CheckIdentityException(SessionExpiredException):
    """Exception raised when a user is requested to re-authenticate."""

    # To log only with debug level in odoo/http.py Application.__call__
    loglevel = logging.DEBUG


class IrHttp(models.AbstractModel):
    _inherit = "ir.http"

    @classmethod
    def _must_check_identity(cls):
        """
        Determine whether the current user session requires identity confirmation.

        This method checks two timeout conditions:
        - `lock_timeout`: maximum allowed session duration before re-authentication is required,
        regardless of user activity.
        - `lock_timeout_inactivity`: period of inactivity after which re-authentication is required.

        It compares the current time to session timestamps and evaluates whether the thresholds have been exceeded:
        - `lock_timeout` compares with the session timestamp `create_time`
        - `lock_timeout_inactivity` compares with the session timestamp `identity-check-next`

        :return: A dictionary describing the re-authentication requirement, or None if no check is needed.

            Possible keys:
            - "logout": True if a full logout is required
            - "check_identity": True if an identity check is required
            - "mfa": True if multi-factor authentication is required
            - "1fa": previously used auth method, to avoid reuse as second factor

        :rtype: dict or None
        """
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
                    res = {reauth_type: True, "mfa": mfa}
                    if mfa:
                        first_fa = session.get("identity-check-1fa")
                        if first_fa:
                            timestamp_1fa, auth_method_1fa = first_fa
                            if timestamp_1fa > threshold:
                                res["1fa"] = auth_method_1fa
                    return res

    @classmethod
    def _check_identity(cls, credential):
        """
        Verify the user's identity using the given credentials.

        Handles both single and multi-factor authentication flows depending on the
        current session state and configured timeout rules.

        :param dict credential: A dictionary containing authentication data. Must include
            a "type" key (e.g., "password", "totp", "webauthn"). If empty, the method
            returns the list of available authentication methods.

        :return: A dictionary indicating the outcome of the identity check:

            - {"auth_methods": [...]} if no credential is provided,
            - {"mfa": True, "auth_methods": [...]} if a second factor is required,
            - None if re-authentication is complete.

        :rtype: dict or None
        """
        check_identity = cls._must_check_identity() or {}
        first_fa = check_identity.get("1fa")
        user = request.env.user
        auth_methods = user._get_auth_methods()
        if not credential:
            if first_fa and first_fa in auth_methods:
                auth_methods.remove(first_fa)
            return {"user_id": user.id, "login": user.login, "auth_methods": auth_methods}

        if credential.get("type") in ("totp", "totp_mail"):
            credential["token"] = int(re.sub(r"\s", "", credential["token"]))

        auth = user._check_credentials(credential, {"interactive": True})

        if first_fa and first_fa != auth["auth_method"]:
            request.session.pop("identity-check-1fa")
        elif auth["mfa"] != "skip" and len(auth_methods) > 1 and check_identity.get("mfa"):
            request.session["identity-check-1fa"] = (time.time(), credential["type"])
            auth_methods.remove(credential["type"])
            return {"mfa": True, "auth_methods": auth_methods}

        request.session.pop("identity-check-next", None)
        request.session["identity-check-last"] = time.time()

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
                root.session_store.save(session)
        elif not inactive and (timestamp := session.get("identity-check-next")) and timestamp > time.time():
            session.pop("identity-check-next")
            # Save manually, websocket requests do not save the session automatically
            root.session_store.save(session)

    @classmethod
    def _authenticate(cls, endpoint):
        """
        Extend the standard `_authenticate` to enforce identity re-confirmation.

        This method checks whether the current session requires identity confirmation due to timeout or inactivity.
        If a logout is required, a `SessionExpiredException` is raised, which the client handles by redirecting
        to the login page.
        If a check identity is required, a `CheckIdentityException` is raised, which the client handles by showing the
        re-authentication dialog.

        :param endpoint: The HTTP route endpoint being accessed.
        :type endpoint: werkzeug.routing.Rule

        :raises CheckIdentityException: If the session requires identity re-confirmation.
        :raises SessionExpiredException: If the session requires a full login.
        :return: None
        """
        super()._authenticate(endpoint)
        if endpoint.routing["auth"] == "user" and request.session.uid is not None:
            if must_check_identity := cls._must_check_identity():
                if must_check_identity.get("logout"):
                    raise SessionExpiredException(f"User {request.session.uid} needs to login again")
                elif endpoint.routing.get("check_identity", True) and must_check_identity.get("check_identity"):
                    raise CheckIdentityException(f"User {request.session.uid} needs to confirm his identity")

    @classmethod
    def _handle_error(cls, exception):
        """
        Handle exceptions raised during request processing.

        If the exception is a `CheckIdentityException` and the route is HTTP-based,
        the user is redirected to the identity confirmation page. This ensures that
        re-authentication can be completed before redirecting to the original request.

        All other exceptions, e.g. `JSONRPC` calls, are handled by displaying the authentication form in a dialog
        rather than a page.

        :param Exception exception: The exception raised during request dispatch.
        :return: An HTTP response for identity confirmation, or the default error response.
        :rtype: werkzeug.wrappers.Response
        """
        if request.dispatcher.routing_type == "http" and isinstance(exception, CheckIdentityException):
            response = request.redirect_query(
                "/auth-timeout/check-identity", {"redirect": request.httprequest.full_path}
            )
            return response
        return super()._handle_error(exception)

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
