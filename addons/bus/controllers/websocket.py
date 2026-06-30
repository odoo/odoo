# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, request, route, SessionExpiredException
from ..models.bus import channel_with_db
from ..websocket import WebsocketConnectionHandler


class WebsocketController(Controller):
    @route('/websocket', type="http", auth="public", cors='*', websocket=True)
    def websocket(self, version=None):
        """
        Handle the websocket handshake, upgrade the connection if successfull.

        :param version: The version of the WebSocket worker that tries to
            connect. Connections with an outdated version will result in the
            websocket being closed. See :attr:`WebsocketConnectionHandler._VERSION`.
        """
        return WebsocketConnectionHandler.open_connection(request, version)

    @route('/websocket/health', type='http', auth='none', save_session=False)
    def health(self):
        data = json.dumps({
            'status': 'pass',
        })
        headers = [('Content-Type', 'application/json'),
                   ('Cache-Control', 'no-store')]
        return request.make_response(data, headers)

    @route('/websocket/peek_notifications', type='jsonrpc', auth='public', cors='*')
    def peek_notifications(self, channels, last, is_first_poll=False):
        if is_first_poll:
            # Used to detect when the current session is expired.
            request.session['is_websocket_session'] = True
        elif 'is_websocket_session' not in request.session:
            raise SessionExpiredException()
        subscribe_data = request.env["ir.websocket"]._prepare_subscribe_data(channels, last)
        request.env["ir.websocket"]._after_subscribe_data(subscribe_data)
        channels_with_db = [channel_with_db(request.db, c) for c in subscribe_data["channels"]]
        notifications = request.env["bus.bus"]._poll(channels_with_db, subscribe_data["last"])
        return {"channels": channels_with_db, "notifications": notifications}

    @route("/websocket/on_closed", type="jsonrpc", auth="public", cors="*")
    def on_websocket_closed(self):
        """Manually notify the closure of a websocket, useful when implementing custom websocket code.
        This is mainly used by Odoo.sh."""
        request.env["ir.websocket"]._on_websocket_closed(request.cookies)

    @route('/bus/websocket_worker_bundle', type='http', auth='public', cors='*')
    def get_websocket_worker_bundle(self, v=None):  # pylint: disable=unused-argument
        """
        :param str v: Version of the worker, frontend only argument used to
            prevent new worker versions to be loaded from the browser cache.
        """
        bundle_name = 'bus.websocket_worker_assets'
        bundle = request.env["ir.qweb"]._get_asset_bundle(bundle_name, debug_assets="assets" in request.session.debug)
        stream = request.env['ir.binary']._get_stream_from(bundle.js())
        return stream.get_response(content_security_policy=None)
