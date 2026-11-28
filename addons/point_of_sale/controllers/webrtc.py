from odoo import http
from odoo.http import request


class PosWebrtcController(http.Controller):

    @http.route("/pos/webrtc/signal", auth="user", type="jsonrpc")
    def webrtc_signal(self, config_id, message):
        """ Relay a WebRTC signaling message from a PoS device to the devices of the config. """
        config = request.env["pos.config"].browse(config_id)
        config.check_access("read")
        config._webrtc_signal(message, config._get_webrtc_session_tag(request.session.sid))
