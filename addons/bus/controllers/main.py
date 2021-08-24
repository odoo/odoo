# Part of Odoo. See LICENSE file for full copyright and licensing details.

import json
import logging
from threading import Thread

from odoo import _, exceptions
from odoo.addons.bus.models.bus import dispatch
from odoo.http import Controller, Response, request, route, ws_routing_map
from odoo.websocket import WebSocket
from odoo.websocket_exceptions import (InvalidVersionException,
                                       WebSocketException)
from werkzeug.exceptions import NotFound

_logger = logging.getLogger(__name__)

class BusController(Controller):

    # ------------------------------------------------------
    # LONG POLLING
    # ------------------------------------------------------

    """ Examples:
    openerp.jsonRpc('/longpolling/poll','call',{"channels":["c1"],last:0}).then(function(r){console.log(r)});
    openerp.jsonRpc('/longpolling/send','call',{"channel":"c1","message":"m1"});
    openerp.jsonRpc('/longpolling/send','call',{"channel":"c2","message":"m2"});
    """

    @route('/longpolling/send', type="json", auth="public")
    def send(self, channel, message):
        if not isinstance(channel, str):
            raise Exception("bus.Bus only string channels are allowed.")
        return request.env['bus.bus'].sendone(channel, message)

    # override to add channels
    def _poll(self, dbname, channels, last, options):
        # update the user presence
        if request.session.uid and 'bus_inactivity' in options:
            request.env['bus.presence'].update(options.get('bus_inactivity'))
        request.cr.close()
        request._cr = None
        return dispatch.poll(dbname, channels, last, options)

    @route('/longpolling/poll', type="json", auth="public", cors="*")
    def poll(self, channels, last, options=None):
        if options is None:
            options = {}
        if not dispatch:
            raise Exception("bus.Bus unavailable")
        if [c for c in channels if not isinstance(c, str)]:
            raise Exception("bus.Bus only string channels are allowed.")
        if request.registry.in_test_mode():
            raise exceptions.UserError(_("bus.Bus not available in test mode"))
        return self._poll(request.db, channels, last, options)

    @route('/longpolling/im_status', type="json", auth="user")
    def im_status(self, partner_ids):
        return request.env['res.partner'].with_context(active_test=False).search([('id', 'in', partner_ids)]).read(['im_status'])

    @route('/longpolling/health', type='http', auth='none', save_session=False)
    def health(self):
        data = json.dumps({
            'status': 'pass',
        })
        headers = [('Content-Type', 'application/json'),
                   ('Cache-Control', 'no-store')]
        return request.make_response(data, headers)

    # ------------------------------------------------------
    # WEBSOCKETS
    # ------------------------------------------------------

    def _handle_handshake(self):
        request.cr.close()
        response = None
        websocket = WebSocket(request, dispatch)
        try:
            websocket.connect()
            request.websocket = websocket
            request.write = websocket.write
        except InvalidVersionException:
            response = Response(status=426, headers={"Sec-WebSocket-Version": str(websocket._version)})
        except WebSocketException as exc:
            response = Response(status=400, response=str(exc))
        return response

    def _handle_websocket_requests(self, routing_map):
        """ Listen for incoming requests, create a cursor for each one then close it after request handling """
        for data in request.websocket.read():
            with request.registry.cursor() as cr:
                try:
                    request.cr = cr
                    channel = data.pop('channel')
                    endpoint, _ = routing_map.match(channel)
                    response = endpoint(data.pop('message'))
                    if response:
                        request.write(response)
                except (NotFound, AttributeError) as exc:
                    request.websocket._handle_exception(exc)
        # Setting cursor to None to prevent WebRequest to try closing an already closed cursor.
        request._cr = None

    def _handle_websocket_notifications(self, websocket):
        for notifications in websocket.read_notifications():
            websocket.write(notifications)

    @route('/websocket', type="http", auth="public")
    def websocket(self):
        """ Proceeds to WebSocket upgrade, then delegate request processing to `_handle_incoming_requests` method """
        response = self._handle_handshake()
        if response:
            return response
        ws_map_adapter = ws_routing_map().bind_to_environ(request.httprequest.environ)
        Thread(target=self._handle_websocket_notifications, args=[request.websocket]).start()
        self._handle_websocket_requests(ws_map_adapter)
        # At this point, we don't mind about status code because those codes are now
        # Handled via WebSocket close frames. Let it be 200.
        return Response(status=200)

    @route('/subscribe', type="websocket")
    def subscribe(self, channels):
        _logger.error('Subscribed to: %s', channels)
        request.websocket.subscribe(channels)

    @route('/bus_inactivity', type="websocket")
    def update_presence(self, data):
        """ With long polling, bus_inactivity was updated at each poll, now that connection stays open,
            We send a bus inactivity update each 30s in order to update the user presence.
        """
        if request.session.uid:
            request.env['bus.presence'].update(data)

    @route('/websocket/testing', type="http", auth="public")
    def websocket_autobahn_testing(self):
        """
            https://github.com/crossbario/autobahn-testsuite is used to validate websockets implementation.
            This route allow us to keep testing the WebSocket protocol with autobahn easily since it expect
            a simple echo of the data which have been sent while we expect JSON to route ws requests.
        """
        response = self._handle_handshake()
        if response:
            return response
        for data in request.websocket.read():
            request.write(data)
        request._cr = None
        return Response(status=200)

    # ------------------------------------------------------
    # DUMMY WEBSOCKET ROUTES
    # ------------------------------------------------------

    @route('/echo', type="websocket")
    def handle_echo_message(self, data):
        return data

    @route('/double_echo', type="websocket")
    def handle_double_echo_message(self, data):
        request.write(data)
        return data

    @route("/subscribe/test", type="websocket")
    def subscribe_test(self, data):
        request.env['bus.bus'].sendone(data.pop('channel'), data.pop('message'))
