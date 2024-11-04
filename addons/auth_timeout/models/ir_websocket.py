from odoo import models
from odoo.http import root
from odoo.addons.bus.websocket import wsrequest


class IrWebsocket(models.AbstractModel):
    _inherit = "ir.websocket"

    def _update_mail_presence(self, inactivity_period):
        """
        Override to track user inactivity via WebSocket presence updates.

        This method extends the base `_update_mail_presence` to update the session's
        inactivity state using the provided inactivity duration from the frontend.

        :param float inactivity_period: Duration of user inactivity in milliseconds.
        :return: None
        """
        self.env["ir.http"]._set_session_inactivity(wsrequest.session, inactivity_period)
        super()._update_mail_presence(inactivity_period)

    def _on_websocket_closed(self, cookies):
        """
        Override to mark the session as inactive when the WebSocket connection closes.

        This ensures that the session is flagged for re-authentication if the user
        closes their last tab, by forcing inactivity tracking when the connection is lost.

        :param dict cookies: A dictionary containing the user's session ID cookie.
        :return: None
        """
        if self.env.user:
            session = root.session_store.get(cookies["session_id"])
            if not session.is_new:
                # `is_new` is a mitigation to avoid calls with arbitrary `session_id`
                # which would create a new session file in the session filestore with an arbitrary name
                # e.g. `env['ir.websocket']._on_websocket_closed({'session_id': 'A'*84})`
                self.env["ir.http"]._set_session_inactivity(session, force=True)
        super()._on_websocket_closed(cookies)
