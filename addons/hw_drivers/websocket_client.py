import json
import logging
import pprint
import requests
import time
import urllib.parse
import websocket

from threading import Thread

from odoo.addons.hw_drivers import main
from odoo.addons.hw_drivers.tools import helpers

_logger = logging.getLogger(__name__)
websocket.enableTrace(True, level=logging.getLevelName(_logger.getEffectiveLevel()))


@helpers.require_db
class WebsocketClient(Thread):
    channel = ""

    def __init__(self, channel, server_url=None):
        """This class will not be instantiated if no db is connected.

        :param str channel: the channel to subscribe to
        :param str server_url: URL of the Odoo server (provided by decorator).
        """
        self.channel = channel
        url_parsed = urllib.parse.urlsplit(server_url)
        scheme = url_parsed.scheme.replace("http", "ws", 1)
        self.url = urllib.parse.urlunsplit((scheme, url_parsed.netloc, 'websocket', '', ''))
        super().__init__()

    def run(self):
        ws = websocket.WebSocketApp(
            self.url,
            header={"User-Agent": "OdooIoTBox/1.0"},
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )

        # The IoT synchronised servers can stop in 2 ways that we need to handle:
        #  A. Gracefully:
        #   In this case a disconnection signal is sent to the IoT-box
        #   The websocket is properly closed, but it needs to be established a new connection when
        #   the server will be back.
        #
        # B. Forced/killed:
        #   In this case there is no disconnection signal received
        #
        #   This will also happen with the graceful quit as `reconnect` will trigger if the server
        #   is offline while attempting the new connection
        while True:
            try:
                run_res = ws.run_forever(reconnect=10)
                _logger.debug("websocket run_forever return with %s", run_res)
            except Exception:
                _logger.exception("An unexpected exception happened when running the websocket")
            _logger.debug('websocket will try to restart in 10 seconds')
            time.sleep(10)

    @staticmethod
    @helpers.require_db
    def send_to_controller(params, server_url=None):
        """Confirm the operation's completion by sending
        a response back to the Odoo server.

        :param params: The parameters to send back to the server
        :param server_url: URL of the Odoo server (provided by decorator).
        """
        try:
            response = requests.post(server_url + "/iot/box/send_websocket", json={'params': params}, timeout=5)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            _logger.exception('Could not reach confirmation status URL: %s', server_url)

    def on_open(self, ws):
        """When the client is set up, this function sends a message
        to subscribe to the iot websocket channel.

        :param ws: The websocket client
        """
        ws.send(
            json.dumps({
                'event_name': 'subscribe',
                'data': {
                    'channels': [self.channel],
                    'last': 0,
                    'mac_address': helpers.get_mac_address()
                }
            })
        )

    @staticmethod
    def on_message(_ws, messages):
        """Synchronously handle messages received by the websocket.

        :param _ws: The websocket client
        :param messages: The message list received by the websocket
        """
        for message in json.loads(messages):
            message = message['message']
            _logger.debug("websocket received a message: %s", pprint.pformat(message))

            msg_type = message['type']
            if msg_type == 'operation_confirmation':
                return
            if msg_type != 'iot_action':
                _logger.warning("Message type not supported: %s", msg_type)
                return

            payload = message['payload']
            iot_box_identifier = payload.get('iot_box_identifier')
            if iot_box_identifier != helpers.get_mac_address():
                # likely intended as IoT Boxes share the same channel
                _logger.debug("Message ignored due to different iot box MAC: %s", iot_box_identifier)
                return

            device_identifier = payload['device_identifier']
            iot_device = main.iot_devices.get(device_identifier)

            # Skip the request if it was already executed (duplicated action calls)
            if not iot_device or not iot_device.is_idempotent(**payload):
                return

            iot_device.action(action=payload.pop('action', ''), **payload)

    @staticmethod
    def on_error(_ws, error):
        _logger.error("websocket received an error: %s", error)

    @staticmethod
    def on_close(_ws, close_status_code, close_msg):
        _logger.debug("websocket closed with status: %s", close_status_code)
