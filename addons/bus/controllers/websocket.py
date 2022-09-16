# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
from werkzeug.exceptions import ServiceUnavailable

from odoo.http import Controller, request, route
from odoo.addons.base.models.assetsbundle import AssetsBundle
from ..models.bus import channel_with_db
from ..websocket import WebsocketConnectionHandler


class WebsocketController(Controller):
    @route('/websocket', type="http", auth="public", cors='*', websocket=True)
    def websocket(self):
        """
        Handle the websocket handshake, upgrade the connection if
        successfull.
        """
        is_headful_browser = request.httprequest.user_agent and 'Headless' not in request.httprequest.user_agent.string
        if request.registry.in_test_mode() and is_headful_browser:
            # Prevent browsers from interfering with the unittests
            raise ServiceUnavailable()
        return WebsocketConnectionHandler.open_connection(request)

    @route('/websocket/health', type='http', auth='none', save_session=False)
    def health(self):
        data = json.dumps({
            'status': 'pass',
        })
        headers = [('Content-Type', 'application/json'),
                   ('Cache-Control', 'no-store')]
        return request.make_response(data, headers)

    @route('/websocket/peek_notifications', type='json', auth='public', cors='*')
    def peek_notifications(self, channels, last):
        channels = list(set(
            channel_with_db(request.db, c)
            for c in request.env['ir.websocket']._build_bus_channel_list(channels)
        ))
        notifications = request.env['bus.bus']._poll(channels, last)
        return {'channels': channels, 'notifications': notifications}

    @route('/websocket/update_bus_presence', type='http', auth='public', cors='*')
    def update_bus_presence(self, inactivity_period):
        request.env['ir.websocket']._update_bus_presence(int(inactivity_period))

    @route('/bus/websocket_worker_bundle', type='http', auth='public', cors='*')
    def get_websocket_worker_bundle(self):
        bundle = 'bus.websocket_worker_assets'
        files, _ = request.env["ir.qweb"]._get_asset_content(bundle)
        asset = AssetsBundle(bundle, files)
        stream = request.env['ir.binary']._get_stream_from(asset.js())
        return stream.get_response()
