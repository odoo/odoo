from werkzeug.exceptions import Unauthorized

from odoo import _, http
from odoo.exceptions import AccessError
from odoo.http import request
from odoo.tools import consteq


class WebrtcRoutes(http.Controller):
    """ Entry points for the WebRTC signaling mesh (pos.config._webrtc_announce/_webrtc_signal).

    peer_group is never a request parameter on either announce route: which route you can
    successfully authenticate against IS your peer_group, fixed server-side either way —
    - /pos/webrtc/announce requires an authenticated pos_user and always announces "terminal".
    - /pos_customer_display/webrtc/announce only requires the config's access token and
      always announces "customer_display".
    Neither identity can be obtained through the other route, regardless of what the
    caller's session or request otherwise looks like.
    """

    # ─── Terminal (authenticated backend user) ─────────────────────────────────

    def _verify_pos_user_config(self, config_id):
        if not request.env.user.has_group("point_of_sale.group_pos_user"):
            raise AccessError(_("Access denied"))
        return request.env["pos.config"].browse(config_id)

    @http.route("/pos/webrtc/announce", auth="user", type="jsonrpc")
    def webrtc_announce(self, config_id, peer_id, device_uuid=None):
        config = self._verify_pos_user_config(config_id)
        return config._webrtc_announce(peer_id, "terminal", device_uuid)

    @http.route("/pos/webrtc/signal", auth="user", type="jsonrpc")
    def webrtc_signal(self, config_id, msg):
        config = self._verify_pos_user_config(config_id)
        return config._webrtc_signal(msg, "terminal")

    # ─── Customer display (public, access-token only) ──────────────────────────

    def _verify_pos_config_token(self, access_token):
        pos_config_sudo = request.env["pos.config"].sudo().search([("access_token", "=", access_token)], limit=1)
        if not pos_config_sudo or not consteq(access_token, pos_config_sudo.access_token):
            message = "Invalid access token"
            raise Unauthorized(message)
        return pos_config_sudo

    @http.route("/pos_customer_display/webrtc/announce", auth="public", type="jsonrpc", website=True)
    def customer_display_webrtc_announce(self, access_token, peer_id, device_uuid=None):
        pos_config_sudo = self._verify_pos_config_token(access_token)
        return pos_config_sudo._webrtc_announce(peer_id, "customer_display", device_uuid)

    @http.route("/pos_customer_display/webrtc/signal", auth="public", type="jsonrpc", website=True)
    def customer_display_webrtc_signal(self, access_token, msg):
        pos_config_sudo = self._verify_pos_config_token(access_token)
        return pos_config_sudo._webrtc_signal(msg, "customer_display")
