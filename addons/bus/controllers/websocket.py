# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json

from odoo.http import Controller, request, route, SessionExpiredException
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
    def peek_notifications(self, channels, last, is_first_poll=False):
        if not all(isinstance(c, str) for c in channels):
            raise ValueError("bus.Bus only string channels are allowed.")
        if is_first_poll:
            # Used to detect when the current session is expired.
            request.session['is_websocket_session'] = True
        elif 'is_websocket_session' not in request.session:
            raise SessionExpiredException()
        channels = list(set(
            channel_with_db(request.db, c)
            for c in request.env['ir.websocket']._build_bus_channel_list(channels)
        ))
        last_known_notification_id = request.env['bus.bus'].sudo().search([], limit=1, order='id desc').id or 0
        if last > last_known_notification_id:
            last = 0
        notifications = request.env['bus.bus']._poll(channels, last)
        return {'channels': channels, 'notifications': notifications}

    @route('/websocket/update_bus_presence', type='json', auth='public', cors='*')
    def update_bus_presence(self, inactivity_period, im_status_ids_by_model):
        if 'is_websocket_session' not in request.session:
            raise SessionExpiredException()
        request.env['ir.websocket']._update_bus_presence(int(inactivity_period), im_status_ids_by_model)
        return {}

    @route('/bus/websocket_worker_bundle', type='http', auth='public', cors='*')
    def get_websocket_worker_bundle(self, v=None):  # pylint: disable=unused-argument
        """
        :param str v: Version of the worker, frontend only argument used to
            prevent new worker versions to be loaded from the browser cache.
        """
        bundle = 'bus.websocket_worker_assets'
        files, _ = request.env["ir.qweb"]._get_asset_content(bundle)
        asset = AssetsBundle(bundle, files)
        stream = request.env['ir.binary']._get_stream_from(asset.js(
            is_minified="assets" not in request.session.debug
        ))
        return stream.get_response(content_security_policy=None)
